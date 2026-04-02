"""
CropSentinel AI -- fast_train.py
Self-contained fast training script.
Writes ALL output to training_log.txt in real time.
Run: python fast_train.py
"""

import os
import sys
import json
import time
import pickle
import random
import warnings

warnings.filterwarnings("ignore")

class Tee:
    def __init__(self, *files):
        self.files = files
    def write(self, obj):
        for f in self.files:
            f.write(obj)
            f.flush()
    def flush(self):
        for f in self.files:
            f.flush()

log_file = open("training_log.txt", "w", encoding="utf-8")
sys.stdout = Tee(sys.stdout, log_file)
sys.stderr = Tee(sys.stderr, log_file)

print("=" * 60)
print("  CropSentinel AI -- FAST TRAINING (sklearn, no downloads)")
print("=" * 60)

t_start = time.time()

print("[1/6] Importing libraries...", flush=True)
import numpy as np
from PIL import Image

print(f"      Done in {time.time()-t_start:.1f}s")

DATASET_PATH     = r"C:\Users\Rohith\OneDrive\Desktop\dataset\plantvillage_dataset\color"
TARGET_CROPS     = ("Apple", "Grape", "Tomato")
MAX_PER_CLASS    = 250
IMG_SIZE         = 64
VALID_EXT        = {".jpg", ".jpeg", ".png", ".bmp"}

print(f"\n[2/6] Scanning dataset: {DATASET_PATH}", flush=True)

all_folders = sorted([
    d for d in os.listdir(DATASET_PATH)
    if os.path.isdir(os.path.join(DATASET_PATH, d))
])
kept = [f for f in all_folders if any(f.startswith(c) for c in TARGET_CROPS)]
class_to_idx = {n: i for i, n in enumerate(kept)}
num_classes  = len(kept)

print(f"      Classes kept: {num_classes}")
for c in kept:
    print(f"        {c}")

os.makedirs("model", exist_ok=True)
with open("model/classes.json", "w") as f:
    json.dump(kept, f, indent=2)
print("      Saved model/classes.json")

random.seed(42)
samples = []
for folder in kept:
    label = class_to_idx[folder]
    fp    = os.path.join(DATASET_PATH, folder)
    files = [x for x in os.listdir(fp)
             if os.path.splitext(x)[1].lower() in VALID_EXT]
    chosen = random.sample(files, min(MAX_PER_CLASS, len(files)))
    for fn in chosen:
        samples.append((os.path.join(fp, fn), label))

random.shuffle(samples)
print(f"      Total images: {len(samples)} ({MAX_PER_CLASS}/class max)")

print(f"\n[3/6] Extracting features (64x64 color histograms)...", flush=True)

def extract_features(path):
    img = Image.open(path).convert("RGB").resize((IMG_SIZE, IMG_SIZE))
    arr = np.array(img, dtype=np.float32) / 255.0
    feats = []
    for c in range(3):
        h, _ = np.histogram(arr[:, :, c], bins=16, range=(0,1))
        feats.append(h.astype(np.float32) / (IMG_SIZE*IMG_SIZE))
    try:
        hsv = np.array(img.convert("HSV"), dtype=np.float32) / 255.0
        for c in range(3):
            h, _ = np.histogram(hsv[:, :, c], bins=16, range=(0,1))
            feats.append(h.astype(np.float32) / (IMG_SIZE*IMG_SIZE))
    except Exception:
        feats.extend([np.zeros(16, dtype=np.float32)] * 3)
    gray = np.array(img.convert("L").resize((16,16)), dtype=np.float32) / 255.0
    feats.append(gray.flatten())
    return np.concatenate(feats)

X_all, y_all = [], []
errors = 0
for i, (path, label) in enumerate(samples):
    try:
        X_all.append(extract_features(path))
        y_all.append(label)
    except Exception as e:
        errors += 1
    if (i+1) % 100 == 0 or (i+1) == len(samples):
        print(f"      {i+1}/{len(samples)} images processed...", flush=True)

X_all = np.array(X_all, dtype=np.float32)
y_all = np.array(y_all)
print(f"      Feature matrix: {X_all.shape} | Errors: {errors}")
print(f"      Done in {time.time()-t_start:.1f}s")

print(f"\n[4/6] Splitting and training LogisticRegression...", flush=True)

class NumpyKNN:
    def __init__(self, k=5):
        self.k = k
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
            nearest = np.argsort(dists)[:self.k]
            nearest_labels = self.y_train[nearest]
            counts = np.bincount(nearest_labels, minlength=num_classes)
            probas.append(counts / self.k)
        return np.array(probas, dtype=np.float32)

    def predict(self, X):
        return np.argmax(self.predict_proba(X), axis=1)

def manual_train_test_split(X, y, test_size=0.2, seed=42):
    np.random.seed(seed)
    indices = np.arange(len(X))
    np.random.shuffle(indices)
    split_idx = int(len(X) * (1 - test_size))
    train_idx, val_idx = indices[:split_idx], indices[split_idx:]
    return X[train_idx], X[val_idx], y[train_idx], y[val_idx]

def simple_f1_score(y_true, y_pred, num_classes):
    f1s = []
    for i in range(num_classes):
        tp = np.sum((y_pred == i) & (y_true == i))
        fp = np.sum((y_pred == i) & (y_true != i))
        fn = np.sum((y_pred != i) & (y_true == i))
        if tp + np.max([fp, fn]) > 0:
            f1s.append(2 * tp / (2 * tp + fp + fn))
        else:
            f1s.append(0.0)
    return np.mean(f1s)

def manual_confusion_matrix(y_true, y_pred, num_classes):
    cm = np.zeros((num_classes, num_classes), dtype=int)
    for t, p in zip(y_true, y_pred):
        cm[t, p] += 1
    return cm

X_train, X_val, y_train, y_val = manual_train_test_split(X_all, y_all, test_size=0.20)
print(f"      Train: {len(X_train)} | Val: {len(X_val)}")

pipe = NumpyKNN(k=5)
pipe.fit(X_train, y_train)
print(f"      Training done in {time.time()-t_start:.1f}s")

print(f"\n[5/6] Evaluating...", flush=True)
y_pred   = pipe.predict(X_val)
accuracy = np.mean(y_pred == y_val)
macro_f1 = simple_f1_score(y_val, y_pred, num_classes)

print(f"\n  {'='*40}")
print(f"  Val Accuracy : {accuracy*100:.1f}%")
print(f"  Val Macro F1 : {macro_f1*100:.1f}%")
print(f"  {'='*40}")

cm = manual_confusion_matrix(y_val, y_pred, num_classes).tolist()
per_class = {}
for i in range(num_classes):
    tp = np.sum((y_pred == i) & (y_val == i))
    fp = np.sum((y_pred == i) & (y_val != i))
    fn = np.sum((y_pred != i) & (y_val == i))
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) > 0 else 0.0
    s = np.sum(y_val == i)
    per_class[kept[i]] = {"precision": round(float(prec),4), "recall": round(float(rec),4),
               "f1": round(float(f1),4), "support": int(s)}

p_all = [per_class[k]["precision"] for k in kept]
r_all = [per_class[k]["recall"] for k in kept]
mp = np.mean(p_all)
mr = np.mean(r_all)

metrics = {"macro_f1": round(float(macro_f1),4), "macro_precision": round(float(mp),4),
           "macro_recall": round(float(mr),4), "accuracy": round(float(accuracy),4),
           "per_class": per_class, "confusion_matrix": cm,
           "class_names": kept, "num_classes": num_classes}
with open("model/validation_metrics.json", "w") as f:
    json.dump(metrics, f, indent=2)

print(f"\n[6/6] Saving model...", flush=True)
ckpt = {
    "arch":          "sklearn_color_hist",
    "classes":       kept,
    "num_classes":   num_classes,
    "best_macro_f1": macro_f1,
    "pipeline_pkl":  pickle.dumps(pipe),
}
with open("model/crop_model.pth", "wb") as f:
    pickle.dump(ckpt, f)

elapsed = time.time() - t_start
print(f"\n{'='*60}")
print(f"  TRAINING COMPLETE in {elapsed:.1f} seconds!")
print(f"  Model : model/crop_model.pth")
print(f"  Classes: model/classes.json")
print(f"  Run 'python app.py' to start the API")
print(f"{'='*60}")

log_file.close()
