# api/routes_mobile.py
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from services.video_stream import generate_frames
from core.state import app_state

# We create a router specifically for mobile
router = APIRouter()

@router.get("/video_feed")
def video_feed():
    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

@router.get("/status")
def get_status():
    return app_state