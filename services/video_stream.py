# services/video_stream.py
import cv2
from threading import Thread
from services.ai_engine import HeuristicEngine
from core.state import app_state

IP_CAMERA_URL = "http://192.168.254.101:8080/video"


class StreamCapture:
    def __init__(self, src):
        self.cap = cv2.VideoCapture(src)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.status, self.frame = self.cap.read()
        self.stopped = False

    def start(self):
        Thread(target=self.update, args=(), daemon=True).start()
        return self

    def update(self):
        while not self.stopped:
            if not self.status:
                self.stop()
            else:
                self.status, self.frame = self.cap.read()

    def stop(self):
        self.stopped = True
        self.cap.release()


def generate_frames():
    stream = StreamCapture(IP_CAMERA_URL).start()
    engine = HeuristicEngine()
    app_state["is_camera_active"] = True

    while not stream.stopped:
        if not stream.status: break

        # Process frame using your exact logic
        annotated_frame = engine.process_frame(stream.frame)

        ret, buffer = cv2.imencode('.jpg', annotated_frame)
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

    stream.stop()
    app_state["is_camera_active"] = False