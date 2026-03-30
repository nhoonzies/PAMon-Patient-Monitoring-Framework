PAMon: Patient Monitoring Framework
PAMon is a modular, two-stage AI framework designed for real-time patient safety monitoring. It utilizes YOLOv8 Pose Estimation for anatomical feature extraction and a temporal heuristic engine to detect falls, slumps, and abnormal postures.

🚀 Key Features
Two-Stage Architecture: Decoupled "Eyes" (YOLOv8) and "Brain" (Heuristic/ML Engine) for high-efficiency edge computing.

Real-Time Monitoring: Low-latency MJPEG streaming compatible with mobile (Flutter) and web interfaces.

Temporal Logic: Advanced timers and grace periods to prevent "flickering" or false positive alarms.

Dual-Interface Support: Native Flutter app for caregivers and a centralized HTML5/Tailwind Admin Dashboard.

🛠 Project Structure
The project is organized into a modular Python architecture for scalability:

main.py: The FastAPI entry point that glues the system together.

api/: Contains modular routes for Mobile (Flutter) and Admin (Web) endpoints.

core/: Manages the global system state and shared memory.

services/: The engine room, containing the ai_engine (YOLO + Heuristics) and video_stream logic.

static/: Frontend assets for the Admin Dashboard.

🚦 Getting Started
1. Prerequisites
Python 3.8+

NVIDIA GPU (Optional, for CUDA acceleration)

IP Webcam App (or a local USB webcam)

2. Installation
Bash
# Clone the repository
git clone https://github.com/nhoonzies/PAMon-Patient-Monitoring-Framework.git

# Install dependencies
pip install fastapi uvicorn ultralytics opencv-python torch
3. Running the Server
Bash
python main.py
Mobile API: http://localhost:8000/video_feed

Admin Dashboard: http://localhost:8000/dashboard

🧠 Methodology
The system uses Skeleton-Based Action Recognition (SBAR). It extracts 17 keypoints from the patient, calculates joint angles and bounding box aspect ratios, and applies temporal filters to validate emergencies before triggering an alert.

Current Version: Heuristic Baseline v2.0 In Progress: Random Forest Time-Series Classification
