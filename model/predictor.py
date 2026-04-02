"""
CropSentinel AI -- model/predictor.py
Production-Compliant Dual Engine: YOLO (Primary) + NumpyKNN (Fallback)
"""

import io
import re
import json
import logging
import os
import pickle
import warnings

warnings.filterwarnings("ignore")
import numpy as np
from PIL import Image

try:
    from ultralytics import YOLO
    ULTRALYTICS_AVAILABLE = True
except ImportError:
    ULTRALYTICS_AVAILABLE = False

logger = logging.getLogger("CropPredictor")

KNOWN_CROPS = ("Apple", "Grape", "Tomato")

IMG_SIZE = 64

def _extract_image_features(img: Image.Image) -> np.ndarray:
    """Fallback Engine Feature Extractor"""
    img = img.resize((IMG_SIZE, IMG_SIZE))
    arr_rgb = np.array(img, dtype=np.float32) / 255.0
    rgb_feat = []
    for c in range(3):
        hist, _ = np.histogram(arr_rgb[:, :, c], bins=16, range=(0, 1))
        rgb_feat.append(hist.astype(np.float32) / (IMG_SIZE * IMG_SIZE))
    try:
        img_hsv_arr = np.array(img.convert("HSV"), dtype=np.float32) / 255.0
    except:
        img_hsv_arr = arr_rgb
    hsv_feat = []
    for c in range(3):
        hist, _ = np.histogram(img_hsv_arr[:, :, c], bins=16, range=(0, 1))
        hsv_feat.append(hist.astype(np.float32) / (IMG_SIZE * IMG_SIZE))
    gray = np.array(img.convert("L").resize((16, 16)), dtype=np.float32) / 255.0
    return np.concatenate(rgb_feat + hsv_feat + [gray.flatten()])

class NumpyKNN:
    def __init__(self, k=5): self.k = k
    def fit(self, X, y):
        self.X_train = np.array(X, dtype=np.float32)
        self.y_train = np.array(y, dtype=np.int32)
        self.mean = np.mean(self.X_train, axis=0)
        self.std = np.std(self.X_train, axis=0) + 1e-8
        self.X_train = (self.X_train - self.mean) / self.std
    def predict_proba(self, X):
        X = np.array(X, dtype=np.float32)
        X = (X - self.mean) / self.std
        num_classes = int(np.max(self.y_train) + 1)
        probas = []
        for i in range(len(X)):
            dists = np.linalg.norm(self.X_train - X[i], axis=1)
            
            weights = 1.0 / (dists + 1e-6)
            nearest = np.argsort(dists)[:self.k]
            nearest_labels = self.y_train[nearest]
            nearest_weights = weights[nearest]
            
            counts = np.bincount(nearest_labels, weights=nearest_weights, minlength=num_classes)
            prob = counts / np.sum(counts)
            
            temp = 0.12
            exp_p = np.exp(prob / temp)
            prob_scaled = exp_p / np.sum(exp_p)
            
            probas.append(prob_scaled)
        return np.array(probas, dtype=np.float32)
    def predict(self, X):
        return np.argmax(self.predict_proba(X), axis=1)

class CropDiseasePredictor:
    """Inference engine prioritizing YOLO; securely falls back to real KNN inference."""

    def __init__(self):
        self.device = "cpu"
        self.model_loaded = False
        self.num_classes = 0
        self.class_names = []
        self._yolo_model = None
        self._knn_model = None
        self._is_yolo = False

        custom_model_path = os.path.join("model", "best.pt")
        fallback_model_path = os.path.join("model", "crop_model.pth")
        
        try:
            if os.path.exists(custom_model_path) and ULTRALYTICS_AVAILABLE:
                logger.info(f"Loading custom YOLO weights from {custom_model_path}...")
                self._yolo_model = YOLO(custom_model_path)
                if hasattr(self._yolo_model, "names"):
                    self.class_names = [self._yolo_model.names[i] for i in range(len(self._yolo_model.names))]
                else:
                    self.class_names = self._yolo_model.model.names
                self._is_yolo = True
                self.model_loaded = True
            elif os.path.exists(fallback_model_path):
                logger.warning(f"best.pt not found. Loading Production Fallback KNN from {fallback_model_path}...")
                import sys
                sys.modules["__main__"].NumpyKNN = NumpyKNN
                with open(fallback_model_path, "rb") as f:
                    ckpt = pickle.load(f)
                self._knn_model = pickle.loads(ckpt["pipeline_pkl"])
                self.class_names = ckpt.get("classes", [])
                self._is_yolo = False
                self.model_loaded = True
            else:
                logger.error("No valid models found. Train YOLO or run fast_train.py!")
                
            self.num_classes = len(self.class_names)
            
        except Exception as e:
            logger.error(f"Failed to load model architecture: {e}")

    def predict(self, image_bytes: bytes) -> dict:
        if not self.model_loaded:
            raise RuntimeError("Model not loaded. Ensure weights exist.")

        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except Exception as e:
            raise ValueError(f"Cannot decode image: {e}")

        if self._is_yolo:
            results = self._yolo_model.predict(image, verbose=False)
            probs = results[0].probs.data.cpu().numpy()
        else:
            feat = _extract_image_features(image).reshape(1, -1)
            probs = self._knn_model.predict_proba(feat)[0]

        top3_idx = np.argsort(probs)[::-1][:min(3, len(probs))]
        
        top_idx_raw = top3_idx[0]
        top_class_raw = self.class_names[top_idx_raw]
        confidence = float(probs[top_idx_raw]) * 100.0
        
        crop, disease = self.parse_class_name(top_class_raw)

        top3 = []
        for i in top3_idx:
            _, c_dis = self.parse_class_name(self.class_names[i])
            top3.append({
                "disease": c_dis,
                "confidence": round(float(probs[i]) * 100, 2),
            })

        return {
            "crop":       crop,
            "disease":    disease,
            "confidence": round(confidence, 2),
            "top3":       top3,
            "raw_class":  top_class_raw,
        }

    def parse_class_name(self, raw_class: str) -> tuple:
        try:
            crop, disease_raw = "Unknown", raw_class
            for known in sorted(KNOWN_CROPS, key=len, reverse=True):
                if known.lower() in raw_class.lower():
                    crop = known
                    break
            
            if "_" in raw_class:
                parts = raw_class.split("_")
                disease_raw = parts[-1] if len(parts) > 1 else raw_class
                
            disease = disease_raw.replace("_", " ").strip()
            if not disease: disease = "Unknown"
            disease = disease.capitalize()
            return (crop, disease)
        except Exception as e:
            return (raw_class, raw_class)
