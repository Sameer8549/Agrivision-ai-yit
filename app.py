"""
CropSentinel AI  -  app.py
FastAPI server  -  5 endpoints: /predict, /health, /metrics, /classes, /train
"""

import json
import logging
import os
import sys
import time
from datetime import datetime

import uvicorn
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  -  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("CropSentinelAPI")

app = FastAPI(
    title="CropSentinel AI",
    description=(
        "AI-powered crop disease detection  -  "
        "Enterprise AI Production 2026. "
        "Pipeline: OpenCV Quality Gate + YOLOv8 + Groq/Llama LLM + HTML5 GPS."
    ),
    version="4.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

predictor    = None
quality_gate = None
geo_engine   = None
llm_router   = None
metrics_tracker = None
_startup_time: float = 0.0
_start_epoch:  float = time.time()


@app.on_event("startup")
async def startup_event():
    global predictor, quality_gate, geo_engine, llm_router, metrics_tracker
    global _startup_time, _start_epoch

    logger.info("CropSentinel AI starting up...")
    t_total = time.perf_counter()
    _start_epoch = time.time()

    t = time.perf_counter()
    from utils.quality_gate import ImageQualityGate
    quality_gate = ImageQualityGate()
    logger.info(f"Loading ImageQualityGate...        done ({time.perf_counter()-t:.2f}s)")

    t = time.perf_counter()
    from model.predictor import CropDiseasePredictor
    predictor = CropDiseasePredictor()
    logger.info(f"Loading CropDiseasePredictor...    done ({time.perf_counter()-t:.2f}s)")

    t = time.perf_counter()
    from utils.geo_context import GeoContextEngine
    geo_engine = GeoContextEngine()
    logger.info(f"Loading GeoContextEngine...        done ({time.perf_counter()-t:.2f}s)")

    t = time.perf_counter()
    from utils.prompt_builder import PromptBuilder  # noqa: F401
    logger.info(f"Loading PromptBuilder...           done ({time.perf_counter()-t:.2f}s)")

    t = time.perf_counter()
    from utils.llm_router import MultiLLMRouter
    llm_router = MultiLLMRouter()
    logger.info(f"Loading MultiLLMRouter...          done ({time.perf_counter()-t:.2f}s)")

    t = time.perf_counter()
    from utils.metrics_tracker import MetricsTracker
    metrics_tracker = MetricsTracker()
    logger.info(f"Loading MetricsTracker...          done ({time.perf_counter()-t:.2f}s)")

    _startup_time = time.perf_counter() - t_total
    logger.info(f"All systems ready. Startup: {_startup_time:.2f}s")


@app.post("/predict")
async def predict(
    image:     UploadFile,
    lat:       float | None = Form(default=None),
    lon:       float | None = Form(default=None),
    timestamp: str   | None = Form(default=None),
):
    """
    Run the full crop disease detection pipeline on an uploaded leaf image.
    Returns structured JSON with crop, disease, severity, and LLM recommendation.
    """
    t0 = time.perf_counter()

    try:
        if predictor is None:
            return JSONResponse(
                status_code=200,
                content={"status": "error", "message": "Server still initialising. Try again shortly."},
            )

        try:
            image_bytes = await image.read()
            if not lat or not lon:
                import io
                from PIL import Image
                from PIL.ExifTags import TAGS, GPSTAGS
                img_exif = Image.open(io.BytesIO(image_bytes))._getexif()
                if img_exif:
                    for t, val in img_exif.items():
                        if TAGS.get(t) == 'GPSInfo':
                            gps = {GPSTAGS.get(k, k): v for k, v in val.items()}
                            if 'GPSLatitude' in gps and 'GPSLongitude' in gps:
                                def _dec(v): return float(v[0]) + float(v[1])/60 + float(v[2])/3600
                                lat_dec = _dec(gps['GPSLatitude'])
                                lon_dec = _dec(gps['GPSLongitude'])
                                if gps.get('GPSLatitudeRef') == 'S': lat_dec = -lat_dec
                                if gps.get('GPSLongitudeRef') == 'W': lon_dec = -lon_dec
                                lat, lon = round(lat_dec, 4), round(lon_dec, 4)
                                logger.info(f"Extracted GeoTags: Lat {lat}, Lon {lon}")

            gps_warning = None
            if lat is None or lon is None:
                gps_warning = "⚠ No embedded GPS metadata detected in image. Agronomic context defaults to fallback region."
            else:
                if not ((6.0 <= lat <= 38.0) and (68.0 <= lon <= 98.0)):
                    gps_warning = f"⚠ GPS Anomaly: Image coordinates ({lat}, {lon}) fall completely outside the authorized crop region. Predictions may lose localized context."

        except Exception as e:
            return JSONResponse(
                status_code=200,
                content={"status": "error", "message": f"Failed to parse uploaded image: {str(e)}"},
            )

        quality_result = quality_gate.check(image_bytes)
        if not quality_result["passed"]:
            return JSONResponse(
                status_code=422,
                content={
                    "status":             "error",
                    "message":            quality_result["rejection_reason"],
                    "image_quality_score": quality_result["quality_score"],
                },
            )

        try:
            pred = predictor.predict(image_bytes)
        except RuntimeError as e:
            return JSONResponse(
                status_code=200,
                content={"status": "error", "message": str(e)},
            )

        crop       = pred["crop"]
        disease    = pred["disease"]
        confidence = pred["confidence"]
        top3       = pred["top3"]

        inference_time_ms = round((time.perf_counter() - t0) * 1000, 1)

        if confidence < 60.0:
            return JSONResponse(
                status_code=422,
                content={
                    "status":           "error",
                    "message":          "Low confidence prediction rejected. Retake photo in better lighting.",
                    "confidence":       confidence,
                    "top3_predictions": top3,
                },
            )

        severity = "HIGH" if confidence > 85.0 else "MODERATE"

        affected_area_base64 = None
        if "healthy" not in disease.lower():
            try:
                import cv2
                import numpy as np
                import base64
                nparr = np.frombuffer(image_bytes, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
                mask_yellow = cv2.inRange(hsv, np.array([15, 50, 50]), np.array([35, 255, 255]))
                mask_brown = cv2.inRange(hsv, np.array([10, 50, 20]), np.array([20, 255, 200]))
                mask_anomaly = cv2.bitwise_or(mask_yellow, mask_brown)
                kernel = np.ones((7,7), np.uint8)
                mask_anomaly = cv2.morphologyEx(mask_anomaly, cv2.MORPH_CLOSE, kernel)
                contours, _ = cv2.findContours(mask_anomaly, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if contours:
                    contours = [c for c in contours if cv2.contourArea(c) > 500]
                    for cnt in contours:
                        x, y, w, h = cv2.boundingRect(cnt)
                        cv2.rectangle(img, (x, y), (x+w, y+h), (0, 0, 255), 4)
                    _, buffer = cv2.imencode('.jpg', img)
                    affected_area_base64 = base64.b64encode(buffer).decode('utf-8')
            except Exception as e:
                logger.warning(f"Affected Area CV Render failed: {e}")

        geo_context = geo_engine.get_context(lat, lon, timestamp)

        recommendation, tier_used = llm_router.route(
            crop, disease, confidence, severity, geo_context, top3
        )

        total_time_ms = round((time.perf_counter() - t0) * 1000, 1)

        logger.info(
            f"[PREDICT] crop={crop} disease={disease.replace(' ', '_')} "
            f"conf={confidence:.1f}% severity={severity} "
            f"quality={quality_result['quality_score']} "
            f"region={geo_context['region_name']} "
            f"llm={tier_used} "
            f"time={total_time_ms}ms"
        )

        return JSONResponse(
            content={
                "status":           "success",
                "crop":             crop,
                "disease":          disease,
                "confidence":       confidence,
                "severity":         severity,
                "top3_predictions": top3,
                "location":         geo_context["region_name"],
                "time_context":     geo_context.get("time_context", geo_context["season"]),
                "seasonal_risk":    geo_context["seasonal_risk"],
                "risk_note":        geo_context["risk_note"],
                "llm_tier_used":    tier_used,
                "recommendation":   recommendation,
                "inference_time_ms":  inference_time_ms,
                "image_quality_score": quality_result["quality_score"],
                "timestamp":        geo_context["timestamp_str"],
                "gps_warning":      gps_warning,
                "affected_area_bs64": affected_area_base64,
            }
        )

    except Exception as e:
        logger.exception(f"Unhandled error in /predict: {e}")
        return JSONResponse(
            status_code=200,
            content={"status": "error", "message": str(e)},
        )


@app.get("/health")
async def health():
    """System health check  -  model status, LLM availability, uptime."""
    try:
        model_loaded  = predictor is not None and predictor.model_loaded
        classes_count = predictor.num_classes if predictor else 0
        device_str    = str(predictor.device) if predictor else "cpu"

        groq_ok    = llm_router.groq_available    if llm_router else False
        mixtral_ok = llm_router.mistral_available if llm_router else False
        ollama_ok  = llm_router.ollama_available() if llm_router else False

        uptime = time.time() - _start_epoch

        return {
            "status":            "healthy",
            "model_loaded":      model_loaded,
            "classes_count":     classes_count,
            "device":            device_str,
            "groq_available":    groq_ok,
            "mixtral_available": mixtral_ok,
            "ollama_available":  ollama_ok,
            "uptime_seconds":    round(uptime, 1),
            "startup_time_seconds": round(_startup_time, 2),
        }
    except Exception as e:
        logger.error(f"/health error: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/metrics")
async def get_metrics():
    """Return last saved validation metrics (Macro F1, per-class, confusion matrix)."""
    try:
        if metrics_tracker is None:
            return {
                "status":  "error",
                "message": "No metrics found. Run training first.",
                "macro_f1": 0.0,
            }
        return metrics_tracker.get_metrics()
    except Exception as e:
        logger.error(f"/metrics error: {e}")
        return {"status": "error", "message": str(e), "macro_f1": 0.0}


@app.get("/classes")
async def list_classes():
    """List all loaded class names parsed into (crop, disease) pairs."""
    try:
        if predictor is None or not predictor.class_names:
            return {"total_classes": 0, "classes": []}

        classes = []
        for raw in predictor.class_names:
            crop, disease = predictor.parse_class_name(raw)
            classes.append({"raw": raw, "crop": crop, "disease": disease})

        return {"total_classes": len(classes), "classes": classes}
    except Exception as e:
        logger.error(f"/classes error: {e}")
        return {"status": "error", "message": str(e)}


def _run_training_background():
    """Background training task  -  runs fast_train.py via subprocess to avoid import hangs."""
    import subprocess
    try:
        logger.info("Starting background training...")
        subprocess.run(["python", "-u", "fast_train.py"], check=True)
        logger.info("Background training successfully completed via fast_train.py.")
    except Exception as e:
        logger.error(f"Background training failed: {e}")


@app.post("/train")
async def start_training(background_tasks: BackgroundTasks):
    """Kick off model training in the background. Returns immediately."""
    background_tasks.add_task(_run_training_background)
    return {
        "status":  "training_started",
        "message": "Training running in background. Check /health for updates.",
    }


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
    )
