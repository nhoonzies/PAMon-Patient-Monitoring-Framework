# services/ai_engine.py
import cv2
import numpy as np
from ultralytics import YOLO
import torch
import time
from core.state import app_state

DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
model = YOLO('yolov8n-pose.pt').to(DEVICE)


class HeuristicEngine:
    def __init__(self):
        # SLUMP TIMERS
        self.fall_start_time = None
        self.last_slump_seen = None
        self.FALL_TIME_LIMIT = 2.0
        self.GRACE_PERIOD = 1.0

        # STANDING TIMERS
        self.stand_start_time = None
        self.last_stand_seen = None
        self.STAND_TIME_LIMIT = 1.5
        self.STAND_GRACE_PERIOD = 1.0

    def calculate_angle(self, a, b, c):
        a, b, c = np.array(a), np.array(b), np.array(c)
        radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
        angle = np.abs(radians * 180.0 / np.pi)
        return 360 - angle if angle > 180.0 else angle

    def process_frame(self, frame):
        results = model.predict(frame, conf=0.4, device=DEVICE, verbose=False, half=True)
        annotated_frame = frame.copy()

        for r in results:
            annotated_frame = r.plot()
            if r.keypoints is not None and len(r.boxes) > 0:
                kpts = r.keypoints.xy[0].cpu().numpy()
                bbox = r.boxes.xyxy[0].cpu().numpy()
                w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]

                status = "ANALYZING..."
                is_alert = False
                color = (0, 255, 255)

                nose_y = kpts[0][1]
                avg_shoulder_y = (kpts[5][1] + kpts[6][1]) / 2 if (kpts[5][1] and kpts[6][1]) else kpts[5][1]

                is_slumping_now = (nose_y > (avg_shoulder_y + 20) and nose_y != 0)
                evaluate_normal_posture = False

                # 1. EVALUATE SLUMP
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

                # 2. EVALUATE NORMAL POSTURE
                if evaluate_normal_posture:
                    if w > (h * 1.5):
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