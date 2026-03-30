import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

# Import our custom modular routers and state
# Ensure these files (api/routes_mobile.py, api/routes_admin.py) exist in your directory
from api.routes_mobile import router as mobile_router
from api.routes_admin import router as admin_router

# 1. Initialize FastAPI
app = FastAPI(
    title="PAMON | Patient Monitoring System",
    description="Backend server for real-time posture analysis and emergency detection.",
    version="2.0.0"
)

# 2. Enable CORS
# This allows your Flutter app and Web Dashboard to talk to the server without being blocked
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Mount Static Files
# This tells FastAPI that the 'static' folder contains our Dashboard HTML/JS
# Make sure you have created a folder named 'static' in your project root
if not os.path.exists("static"):
    os.makedirs("static")
    print("Warning: 'static' folder created. Please add index.html and script.js.")

app.mount("/static", StaticFiles(directory="static"), name="static")

# 4. Include Modular Routers
# The mobile router handles /video_feed and /status for the Flutter app
app.include_router(mobile_router)

# The admin router handles dashboard-specific data under the /admin prefix
app.include_router(admin_router, prefix="/admin")

# 5. Dashboard Entry Point
# Access this at http://localhost:8000/dashboard
@app.get("/dashboard")
async def get_dashboard():
    """Serves the Admin Dashboard HTML file."""
    return FileResponse('static/index.html')

# 6. Root Health Check
@app.get("/")
async def root():
    return {
        "system": "PAMON Backend",
        "status": "Online",
        "dashboard_url": "/dashboard",
        "api_docs": "/docs"
    }

# 7. Start the Server
if __name__ == "__main__":
    # We use '0.0.0.0' so other devices on your local Wi-Fi (like your phone) can connect
    print("--- Launching PAMON System ---")
    print("Mobile Stream: http://localhost:8000/video_feed")
    print("Admin Dashboard: http://localhost:8000/dashboard")
    uvicorn.run(app, host="0.0.0.0", port=8000)