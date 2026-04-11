# services/ai_engine.py
import cv2
import numpy as np
from ultralytics import YOLO
import torch
import time
import joblib
import warnings
import os
from collections import deque, Counter
from core.state import app_state

# --- SILENCE SCIKIT-LEARN WARNINGS ---
warnings.filterwarnings("ignore", message="X does not have valid feature names")
warnings.filterwarnings("ignore", category=UserWarning, module="sklearn.utils.parallel")

# ⚠️ FORCED CPU MODE FOR AMD RYZEN
DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
model = YOLO('yolov8n-pose.pt').to(DEVICE)

# --- 1. LOAD THE ML BRAIN ---
MODEL_FILENAME = "pamon_brain_v2.joblib"
try:
    rf_model = joblib.load(MODEL_FILENAME)
    print(f"--- Machine Learning Brain ({MODEL_FILENAME}) Loaded Successfully ---")
except FileNotFoundError:
    print(f"--- ERROR: {MODEL_FILENAME} not found. Please ensure it is in the same folder as main.py ---")
    print("--- System defaulting to Heuristics Only ---")
    rf_model = None


class HeuristicEngine:
    def __init__(self):
        self.WINDOW_SIZE = 15
        self.pose_window = deque(maxlen=self.WINDOW_SIZE)

        self.prediction_buffer = deque(maxlen=12)

        self.last_xy = np.zeros((17, 2))

        self.ml_emergency_start = None
        self.last_ml_emergency_seen = None
        self.ML_EMERGENCY_LIMIT = 1.0

        self.fall_start_time = None
        self.last_slump_seen = None
        self.FALL_TIME_LIMIT = 2.0
        self.GRACE_PERIOD = 1.0

        self.stand_start_time = None
        self.last_stand_seen = None
        self.STAND_TIME_LIMIT = 1.5
        self.STAND_GRACE_PERIOD = 1.0

    def calculate_angle(self, a, b, c):
        a, b, c = np.array(a), np.array(b), np.array(c)
        radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
        angle = np.abs(radians * 180.0 / np.pi)
        return 360 - angle if angle > 180.0 else angle

    def safe_dist(self, p1, p2):
        return np.linalg.norm(np.array(p1) - np.array(p2)) if (p1[0] != 0 and p2[0] != 0) else 0

    def process_frame(self, frame):
        results = model.predict(frame, conf=0.45, device=DEVICE, verbose=False)
        annotated_frame = frame.copy()

        for r in results:
            annotated_frame = r.plot()
            if r.keypoints is not None and len(r.boxes) > 0:

                boxes_np = r.boxes.xyxy.cpu().numpy()
                areas = [(b[2] - b[0]) * (b[3] - b[1]) for b in boxes_np]
                target_idx = np.argmax(areas)
                max_area = areas[target_idx]

                if max_area < 8000:
                    continue

                kpts = r.keypoints.xy[target_idx].cpu().numpy()
                bbox = boxes_np[target_idx]
                conf = r.keypoints.conf[target_idx].cpu().numpy() if r.keypoints.conf is not None else np.ones(17)

                w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
                is_laying_down_override = (w > (h * 1.5))
                body_size = max(w, h)

                # ==========================================
                # PHASE 1: THE ML BRAIN
                # ==========================================
                raw_ml_prediction = "Normal_Baseline"

                if len(self.pose_window) == 0: self.last_xy = kpts.copy()

                prev_kpts = self.last_xy.copy()
                v_xy = kpts - prev_kpts
                self.last_xy = kpts.copy()

                hip_x = (kpts[11][0] + kpts[12][0]) / 2.0
                hip_y = (kpts[11][1] + kpts[12][1]) / 2.0

                if hip_x == 0 and hip_y == 0:
                    hip_x = (bbox[0] + bbox[2]) / 2.0
                    hip_y = (bbox[1] + bbox[3]) / 2.0

                scale = h if h > 10 else 1.0

                frame_features = []
                for j in range(17):
                    rel_x = (kpts[j][0] - hip_x) / scale if kpts[j][0] != 0 else 0
                    rel_y = (kpts[j][1] - hip_y) / scale if kpts[j][1] != 0 else 0
                    v_x = v_xy[j][0] / scale
                    v_y = v_xy[j][1] / scale

                    frame_features.extend([rel_x, rel_y, conf[j], v_x, v_y])

                self.pose_window.append(frame_features)

                if rf_model and len(self.pose_window) == self.WINDOW_SIZE:
                    flat_window = []
                    for f in self.pose_window: flat_window.extend(f)
                    input_data = np.array(flat_window).reshape(1, -1)
                    raw_ml_prediction = rf_model.predict(input_data)[0]

                # ==========================================
                # THE HEURISTIC VETOS
                # ==========================================
                def get_v(idx):
                    if kpts[idx][0] == 0 or prev_kpts[idx][0] == 0: return 0
                    return np.linalg.norm(v_xy[idx]) / scale

                # 1. REACHING VETO
                if raw_ml_prediction == "Emergency_Reaching":
                    v_l_wrist = get_v(9)
                    v_r_wrist = get_v(10)

                    # MIDDLE GROUND: Lowered from 0.40 to 0.30
                    if max(v_l_wrist, v_r_wrist) > 0.30:
                        raw_ml_prediction = "Emergency_Thrashing"
                    else:
                        sh_x = (kpts[5][0] + kpts[6][0]) / 2 if kpts[5][0] and kpts[6][0] else 0
                        sh_y = (kpts[5][1] + kpts[6][1]) / 2 if kpts[5][1] and kpts[6][1] else 0
                        hip_x = (kpts[11][0] + kpts[12][0]) / 2 if kpts[11][0] and kpts[12][0] else 0
                        hip_y = (kpts[11][1] + kpts[12][1]) / 2 if kpts[11][1] and kpts[12][1] else 0

                        torso_length = 0
                        if sh_x != 0 and hip_x != 0:
                            torso_length = np.linalg.norm([sh_x - hip_x, sh_y - hip_y])

                        # Adjusted baseline ratio slightly for better accuracy
                        torso_length = torso_length if torso_length > (body_size * 0.35) else (body_size * 0.35)

                        # MIDDLE GROUND: Standard reach is 1.05x torso length
                        reach_threshold = torso_length * 1.05

                        # MIDDLE GROUND: Laying down reach is 1.25x torso length
                        if is_laying_down_override:
                            reach_threshold = torso_length * 1.25

                        dist_l_arm = self.safe_dist(kpts[9], kpts[5]) if conf[9] > 0.5 else 0
                        dist_r_arm = self.safe_dist(kpts[10], kpts[6]) if conf[10] > 0.5 else 0

                        if max(dist_l_arm, dist_r_arm) < reach_threshold:
                            raw_ml_prediction = "Normal_Baseline"

                # 2. THRASHING VETO
                elif raw_ml_prediction == "Emergency_Thrashing":
                    v_l_hip = get_v(11)
                    v_r_hip = get_v(12)

                    if not is_laying_down_override and max(v_l_hip, v_r_hip) > 0.20:
                        raw_ml_prediction = "Normal_Baseline"
                    else:
                        valid_limb_vs = []
                        for idx in [9, 10, 15, 16]:
                            if kpts[idx][0] != 0 and prev_kpts[idx][0] != 0 and conf[idx] > 0.5:
                                valid_limb_vs.append(np.linalg.norm(v_xy[idx]) / scale)

                        # MIDDLE GROUND: Dropped the Tornado Gate from 0.40 down to 0.30.
                        # This easily catches actual thrashing, but filters out standard rolling/shifting.
                        if len(valid_limb_vs) == 0 or max(valid_limb_vs) < 0.30:
                            raw_ml_prediction = "Normal_Baseline"

                # ==========================================
                # THE SMOOTHING BUFFER
                # ==========================================
                self.prediction_buffer.append(raw_ml_prediction)

                if len(self.prediction_buffer) == self.prediction_buffer.maxlen:
                    smoothed_prediction = Counter(self.prediction_buffer).most_common(1)[0][0]
                else:
                    smoothed_prediction = "Normal_Baseline"

                # ==========================================
                # ML PRIORITY TRIGGER
                # ==========================================
                if smoothed_prediction in ["Emergency_Reaching", "Emergency_Pain", "Emergency_Thrashing"]:
                    if self.ml_emergency_start is None:
                        self.ml_emergency_start = time.time()

                    self.last_ml_emergency_seen = time.time()

                    if time.time() - self.ml_emergency_start >= self.ML_EMERGENCY_LIMIT:
                        app_state["status"] = smoothed_prediction.replace("_", " ").upper()
                        app_state["is_alert"] = True
                        color = (0, 0, 255)

                        cv2.rectangle(annotated_frame, (10, 10), (600, 75), (0, 0, 0), -1)
                        cv2.putText(annotated_frame, f"STATUS: {app_state['status']}", (20, 55),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 3)
                        return annotated_frame
                else:
                    if self.last_ml_emergency_seen and (time.time() - self.last_ml_emergency_seen > 1.0):
                        self.ml_emergency_start = None
                        self.last_ml_emergency_seen = None

                # ==========================================
                # PHASE 2: YOUR HEURISTICS
                # ==========================================
                status = "ANALYZING..."
                is_alert = False
                color = (0, 255, 255)

                nose_y = kpts[0][1]
                avg_shoulder_y = (kpts[5][1] + kpts[6][1]) / 2 if (kpts[5][1] and kpts[6][1]) else kpts[5][1]

                is_slumping_now = (nose_y > (avg_shoulder_y + 20) and nose_y != 0)
                evaluate_normal_posture = False

                if is_slumping_now:
                    if self.fall_start_time is None: self.fall_start_time = time.time()
                    self.last_slump_seen = time.time()
                    time_slumped = time.time() - self.fall_start_time

                    if time_slumped >= self.FALL_TIME_LIMIT:
                        status = "FALL/SLUMP DETECTED"
                        is_alert = True
                        color = (0, 0, 255)
                    else:
                        time_left = round(self.FALL_TIME_LIMIT - time_slumped, 1)
                        status = f"SLUMP WARNING ({time_left}s)..."
                        is_alert = True
                        color = (0, 165, 255)

                    self.stand_start_time = None
                    self.last_stand_seen = None
                else:
                    if self.last_slump_seen is not None:
                        if time.time() - self.last_slump_seen > self.GRACE_PERIOD:
                            self.fall_start_time, self.last_slump_seen = None, None
                            evaluate_normal_posture = True
                        else:
                            status = "SIGNAL LOST - HOLDING TIMER..."
                            is_alert = True
                            color = (0, 165, 255)
                    else:
                        evaluate_normal_posture = True

                if evaluate_normal_posture:
                    if is_laying_down_override:
                        status = "LAYING DOWN"
                        color = (0, 255, 0)
                        self.stand_start_time = None
                        self.last_stand_seen = None
                    else:
                        try:
                            angle = self.calculate_angle(kpts[5], kpts[11], kpts[13])
                            is_standing_now = not (50 < angle < 135)

                            if is_standing_now:
                                if self.stand_start_time is None: self.stand_start_time = time.time()
                                self.last_stand_seen = time.time()
                                time_stood = time.time() - self.stand_start_time

                                if time_stood >= self.STAND_TIME_LIMIT:
                                    status = "STANDING"
                                    is_alert = True
                                    color = (0, 165, 255)
                                else:
                                    status = "CHECKING POSTURE..."
                                    color = (0, 255, 255)
                            else:
                                if self.last_stand_seen is not None:
                                    if time.time() - self.last_stand_seen > self.STAND_GRACE_PERIOD:
                                        self.stand_start_time = None
                                        self.last_stand_seen = None
                                        status = "SITTING"
                                        color = (0, 255, 0)
                                    else:
                                        status = "CHECKING POSTURE..."
                                        color = (0, 255, 255)
                                else:
                                    status = "SITTING"
                                    color = (0, 255, 0)
                        except:
                            pass

                app_state["status"] = status
                app_state["is_alert"] = is_alert

                cv2.rectangle(annotated_frame, (10, 10), (600, 75), (0, 0, 0), -1)
                cv2.putText(annotated_frame, f"STATUS: {status}", (20, 55),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 3)

        return annotated_frame
