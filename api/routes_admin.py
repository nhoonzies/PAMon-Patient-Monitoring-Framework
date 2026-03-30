# api/routes_admin.py
from fastapi import APIRouter
from core.state import app_state

router = APIRouter()

@router.get("/system_health")
def get_system_health():
    """A future endpoint for the dashboard to check if the camera/AI is online."""
    return {
        "camera_active": app_state["is_camera_active"],
        "current_patient_status": app_state["status"]
    }