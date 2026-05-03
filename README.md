# PAMon: A Real-Time Computer Vision Framework For In-Patient Activity Classification Using YOLOv8-Pose 


**PAMon** is a high-performance, modular AI framework designed for real-time patient safety and emergency detection. It combines **YOLOv8 Pose Estimation** with a custom temporal heuristic engine to bridge the gap between computer vision and actionable medical alerts.

---

## 🛠 System Architecture
The framework follows a **Two-Stage Skeleton-Based Action Recognition (SBAR)** pipeline:

1.  **Stage 1 (Feature Extraction):** A YOLOv8-pose model identifies 17 anatomical keypoints in real-time.
2.  **Stage 2 (Classification):** A heuristic engine and future Random Forest ML model analyzes joint angles, bounding box aspect ratios, and movement velocity to classify patient states.



---

## 📂 Project Structure
This project uses a modular FastAPI architecture to ensure scalability and separation of concerns:

* **`main.py`**: The central hub that connects the AI services to the web APIs.
* **`api/`**: 
    * `routes_mobile.py`: High-speed endpoints for the Flutter mobile application.
    * `routes_admin.py`: Specialized endpoints for the web-based dashboard.
* **`core/`**: 
    * `state.py`: The "Global Brain" that stores real-time patient status.
* **`services/`**: 
    * `ai_engine.py`: Contains the logic for posture math, timers, and YOLO processing.
    * `video_stream.py`: Manages the IP Camera connection and MJPEG byte-streaming.
* **`static/`**: Frontend assets (HTML/JS) for the Admin Dashboard.

---

## 🚥 Real-Time Detection Logic
The system currently implements a **Heuristic Baseline** with temporal validation:

* **Fall/Slump Detection:** Triggers if the head (nose) drops below a specific threshold relative to the hips or if the bounding box becomes horizontal.
* **Standing Detection:** Uses joint angle calculations (Knee/Hip/Shoulder) with a 1.5s validation timer to reduce false positives.
* **Grace Periods:** Implements a 1.0s "Hold" state to handle momentary camera occlusions or network lag.
* * **Thrashing/Reaching Detection: ** With the new ML trained and added, the framework can now detect thrashing and reaching emergencies.

---

## 🛠 Snapshots and Demos
<img width="1873" height="911" alt="Screenshot 2026-04-21 231719" src="https://github.com/user-attachments/assets/4f3bc06b-c2f1-4e42-b154-72638fa1c933" />

** Click here for demo video: **
[![Demo Video](https://img.youtube.com/vi/BxgT6zZuL5w/0.jpg)](https://www.youtube.com/watch?v=BxgT6zZuL5w)


## 💻 Getting Started

### 1. Installation
```bash
# Clone the repository
git clone [https://github.com/nhoonzies/PAMon-Patient-Monitoring-Framework.git](https://github.com/nhoonzies/PAMon-Patient-Monitoring-Framework.git)

# Install dependencies
pip install fastapi uvicorn ultralytics opencv-python torch

