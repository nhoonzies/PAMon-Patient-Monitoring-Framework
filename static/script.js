// static/script.js

// --- 1. INITIALIZE DATA ---
let lastStatus = "CONNECTING...";
let sessionLogs = [];
let isMuted = false;

const statusText = document.getElementById('status-text');
const statusCard = document.getElementById('status-card');
const alertBorder = document.getElementById('alert-border');
const ackBtn = document.getElementById('ack-btn');
const streamImg = document.getElementById('live-stream');
const logContainer = document.getElementById('log-container');
const logCount = document.getElementById('log-count');
const rawTextLog = document.getElementById('raw-text-log');

// --- 2. MOTION GRAPH SETUP ---
const ctx = document.getElementById('motionChart').getContext('2d');
const motionChart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: Array(30).fill(''),
        datasets: [{
            data: Array(30).fill(0),
            borderColor: '#14b8a6',
            backgroundColor: 'rgba(20, 184, 166, 0.1)',
            borderWidth: 2,
            fill: true,
            tension: 0.4,
            pointRadius: 0
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: { y: { display: false, min: 0, max: 100 }, x: { display: false } },
        plugins: { legend: { display: false } }
    }
});

// --- 3. SEVERITY CATEGORIZER ---
function getSeverity(status) {
    if (status.includes("EMERGENCY") || status.includes("SLUMP") || status.includes("FALL")) return 'danger';
    if (status.includes("SITTING") || status.includes("STANDING") || status.includes("CHECKING")) return 'warning';
    return 'safe';
}

const uiColors = {
    'danger': { text: 'text-red-500', bg: 'bg-red-950/40', border: 'border-red-600' },
    'warning': { text: 'text-orange-400', bg: 'bg-orange-950/30', border: 'border-orange-500/50' },
    'safe': { text: 'text-green-400', bg: 'bg-green-950/20', border: 'border-green-500/30' }
};

// --- 4. THE SNAPSHOT CAPTURE ENGINE ---
function takeSnapshot() {
    const canvas = document.getElementById('snapshot-canvas');
    const context = canvas.getContext('2d');
    context.drawImage(streamImg, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL('image/jpeg', 0.7);
}

// --- 5. THE NEW FILTERED LOGGING FUNCTION ---
// Notice the new "isAlert" parameter
function addToLog(status, severity, isAlert) {
    const timestamp = new Date().toLocaleTimeString();
    const colorClass = uiColors[severity].text;
    const borderClass = uiColors[severity].border;

    // --- A. THE VISUAL TIMELINE ENTRY (ONLY FIRES IF IT'S AN ALERT) ---
    if (isAlert) {
        const snapshot = takeSnapshot();
        const entry = { time: timestamp, event: status, img: snapshot, color: colorClass, border: borderClass };
        sessionLogs.unshift(entry);
        logCount.innerText = `${sessionLogs.length} Events`;

        if (sessionLogs.length > 0) document.getElementById('empty-log-msg').classList.add('hidden');

        logContainer.innerHTML = sessionLogs.map(log => `
            <div class="bg-slate-800/40 p-2 rounded-xl border ${log.border} animate-in fade-in slide-in-from-right-4 duration-500">
                <div class="flex justify-between text-[10px] mb-1 font-bold uppercase tracking-widest">
                    <span class="${log.color}">${log.event}</span>
                    <span class="text-slate-400">${log.time}</span>
                </div>
                <img src="${log.img}" class="w-full h-20 object-cover rounded-lg border border-slate-700 shadow-inner">
            </div>
        `).join('');
    }

    // --- B. THE RAW TEXT LOG ENTRY (FIRES FOR ALL EVENTS) ---
    const logNode = document.createElement('div');
    logNode.className = `border-l-2 pl-2 py-0.5 ${borderClass} animate-in fade-in slide-in-from-right-2 duration-300`;
    logNode.innerHTML = `<span class="text-slate-500">[${timestamp}]</span> <span class="${colorClass} font-bold">${status}</span>`;
    rawTextLog.prepend(logNode);
}


// --- 6. ALERT ACKNOWLEDGEMENT ---
function acknowledgeAlert() {
    isMuted = true;
    alertBorder.classList.add('hidden');
    ackBtn.classList.add('hidden');
    statusCard.className = "bg-slate-900 p-4 rounded-2xl border border-slate-800 shadow-xl text-center transition-colors duration-300 shrink-0";

    // Log the acknowledgement
    const timestamp = new Date().toLocaleTimeString();
    const logNode = document.createElement('div');
    logNode.className = `border-l-2 pl-2 py-0.5 border-slate-600 animate-in fade-in duration-300`;
    logNode.innerHTML = `<span class="text-slate-500">[${timestamp}]</span> <span class="text-slate-400 italic">Alert Acknowledged by Staff</span>`;
    rawTextLog.prepend(logNode);
}

// --- 7. CORE MONITORING LOOP ---
async function fetchUpdate() {
    const start = Date.now();
    try {
        const res = await fetch('/status');
        const data = await res.json();

        if (data.status !== lastStatus && data.status !== "ANALYZING...") {
            const severity = getSeverity(data.status);

            // Pass the data.is_alert flag to the logging function
            addToLog(data.status, severity, data.is_alert);

            statusText.innerText = data.status;
            statusText.className = `text-3xl font-black italic ${uiColors[severity].text}`;
            statusCard.className = `${uiColors[severity].bg} p-4 rounded-2xl border ${uiColors[severity].border} shadow-xl text-center transition-colors duration-300 shrink-0`;

            // If it's a danger state, trigger the red flashing border
            if (severity === 'danger') {
                isMuted = false;
                alertBorder.classList.remove('hidden');
                ackBtn.classList.remove('hidden');
            } else {
                alertBorder.classList.add('hidden');
                ackBtn.classList.add('hidden');
            }

            lastStatus = data.status;
        }

        // Motion Chart Logic
        let intensity = 5;
        if (lastStatus.includes("SITTING") || lastStatus.includes("STANDING")) intensity = Math.random() * 20 + 20;
        if (data.is_alert) intensity = Math.random() * 40 + 60;

        motionChart.data.datasets[0].data.push(intensity);
        motionChart.data.datasets[0].data.shift();

        motionChart.data.datasets[0].borderColor = data.is_alert ? '#ef4444' : '#14b8a6';
        motionChart.data.datasets[0].backgroundColor = data.is_alert ? 'rgba(239, 68, 68, 0.1)' : 'rgba(20, 184, 166, 0.1)';
        motionChart.update('none');

        document.getElementById('latency-text').innerText = (Date.now() - start) + "ms";

    } catch (e) {
        console.warn("Connection to Python Backend Lost");
    }
}

setInterval(fetchUpdate, 500);