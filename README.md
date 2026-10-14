<div align="center">
  <h1>🌱 AgriVision</h1>
  <p><strong></p>
</div>

An enterprise-grade agricultural diagnostic platform that merges real-time Computer Vision with localized Mixture-of-Experts Artificial Intelligence. Built for high-speed edge environments, AgriVision can instantly detect multi-crop pathologies, calculate localized spraying windows, and generate professional PDF lab reports fully connected to regional farming expert networks.

---

## 🏗️ Architecture Stack
- **Frontend Ecosystem:** React.js + Vanilla CSS (Cinematic Glassmorphism UI & Dynamic Print Media Engine)
- **Backend Routing:** FastAPI (Python), Uvicorn HTTP Engine 
- **Computer Vision Core:** Ultralytics YOLOv8 CNN (Classification Pipeline) + OpenCV (Dynamic Bounding Box Visualization)
- **Generative AI Engine:** Multi-Tier LLM Router utilizing **Mixtral 8x7B via Groq** for zero-latency structured JSON generation
- **Failover Security:** Custom pure-NumPy Offline KNN Architecture intercept fallback

## ⚙️ Intelligent Workflow Pipeline
1. **Quality Gate Execution:** An uploaded localized biological sample is checked for lighting/focus.
2. **Vision Inference:** The payload routes into our trained YOLOv8 Tensor weights (`best.pt`) to execute a rapid multi-class prediction matrix.
3. **Anomaly Visualization:** If a pathology is flagged, OpenCV intercepts the Base64 stream and dynamically burns targeting squares (bounding boxes) over suspected necrotic zones on the leaf.
4. **Geo-Temporal Structuring:** Live system clocks (e.g., Early Morning conditions) and geolocation data (Mangalore Region) augment the diagnostic payload.
5. **AI Treatment Routing:** The payload is processed by the Mixtral 8x7B MoE. It deterministically returns serialized JSON containing a 5-step localized Action Plan, Est. Recovery, and Preventive Notes.
6. **Delivery & Deployment:** The React dashboard binds the data, exposes direct WhatsApp API links to our KVK Mangalore expert network, and unlocks a 1-click A4 PDF Report Download.

## 🔌 Integrations & APIs 
* **Groq Inference SDK:** Secures our edge processing speeds by utilizing Groq's LPU architecture to fire the Mistral/Llama3 models practically instantly. Highly cost-effective for agricultural scaling.
* **WhatsApp API (`wa.me`):** Deep-linked directly into our Local Farmer Expert Network UI to remove friction in finding local KVK help (e.g., Dr. T. J. Ramesh).
* **PDF Engine:** Our hidden DOM engine hijacks the standard `window.print()` browser API to force-render a fully branded, watermarked 8.5x11 printed diagnostic sheet.

---

## 🚀 How to Run Locally

### 1. Initialize the Python Backend
Ensure you have the required dependencies (Ultralytics, FastAPI, Uvicorn, Groq). Run the inference engine from the absolute root of the project folder:
```bash
python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```
*Wait for the console message recognizing your `best.pt` architecture load.*

### 2. Initialize the React Dashboard
Open a completely separate/new terminal window. Navigate into the frontend sub-layer and launch the static Node/Python server:
```bash
cd frontend
python -m http.server 8080
```

### 3. Connect
Open your browser and navigate to:
**👉 [http://localhost:8080](http://localhost:8080)**

---
*Built organically for the Matrix Fusion 4.0 Hackathon.*
