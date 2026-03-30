async function updateDashboard() {
    const startTime = Date.now();
    try {
        const response = await fetch('/status'); // Using existing status endpoint
        const data = await response.json();

        const statusEl = document.getElementById('patient-status');
        const cardEl = document.getElementById('status-card');
        const latencyEl = document.getElementById('latency');

        // Update Text
        statusEl.innerText = data.status;

        // Visual Alarm Logic
        if (data.is_alert) {
            cardEl.classList.add('alert-active');
            statusEl.classList.add('text-white');
        } else {
            cardEl.classList.remove('alert-active');
            statusEl.classList.remove('text-white');
        }

        // Calculate Latency
        latencyEl.innerText = (Date.now() - startTime) + "ms";

    } catch (error) {
        console.error("Dashboard Sync Error:", error);
        document.getElementById('camera-status').innerText = "DISCONNECTED";
        document.getElementById('camera-status').classList.replace('bg-green-500', 'bg-red-500');
    }
}

// Polling: Update every 500ms
setInterval(updateDashboard, 500);