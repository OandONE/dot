"""Dot Web Panel - Privacy Indicator Dashboard"""

from flask import Flask, jsonify, render_template_string
import sqlite3
import os
import subprocess

app = Flask(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'dot.db')

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dot - Privacy Panel</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', sans-serif; background: #1a1a2e; color: #eee; padding: 20px; }
        .container { max-width: 800px; margin: 0 auto; }
        h1 { text-align: center; color: #00ff88; margin-bottom: 30px; }
        .card { background: #16213e; border-radius: 12px; padding: 20px; margin-bottom: 20px; }
        .card h2 { color: #00ff88; margin-bottom: 15px; }
        .status { display: flex; gap: 20px; justify-content: center; flex-wrap: wrap; }
        .device { text-align: center; padding: 20px; border-radius: 8px; min-width: 150px; }
        .active { background: #ff4444; }
        .inactive { background: #333; }
        .dot { width: 20px; height: 20px; border-radius: 50%; display: inline-block; margin-right: 8px; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #333; }
        th { color: #00ff88; }
        .btn { background: #ff4444; color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-size: 16px; }
        .btn:hover { background: #cc0000; }
        .refresh { color: #888; font-size: 12px; text-align: center; margin-top: 20px; }
    </style>
    <script>
        async function loadStatus() {
            const res = await fetch('/api/status');
            const data = await res.json();
            document.getElementById('cam-status').textContent = data.camera ? '🟢 Active' : '⚪ Inactive';
            document.getElementById('cam-status').parentElement.className = 'device ' + (data.camera ? 'active' : 'inactive');
            document.getElementById('mic-status').textContent = data.microphone ? '🟢 Active' : '⚪ Inactive';
            document.getElementById('mic-status').parentElement.className = 'device ' + (data.microphone ? 'active' : 'inactive');
        }
        async function killAll() {
            if(confirm('Kill all apps using devices?')) {
                await fetch('/api/kill');
                loadStatus();
            }
        }
        setInterval(loadStatus, 2000);
        window.onload = loadStatus;
    </script>
</head>
<body>
    <div class="container">
        <h1>🟢 Dot Privacy Panel</h1>
        
        <div class="card">
            <h2>Device Status</h2>
            <div class="status">
                <div class="device inactive">
                    <h3>📷 Camera</h3>
                    <p id="cam-status">⚪ Inactive</p>
                </div>
                <div class="device inactive">
                    <h3>🎤 Microphone</h3>
                    <p id="mic-status">⚪ Inactive</p>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>Recent History</h2>
            <table>
                <tr><th>Time</th><th>Device</th><th>Process</th><th>Duration</th></tr>
                {% for row in history %}
                <tr>
                    <td>{{ row[0] }}</td>
                    <td>{{ row[1] }}</td>
                    <td>{{ row[2] }}</td>
                    <td>{{ row[3] }}s</td>
                </tr>
                {% endfor %}
                {% if not history %}
                <tr><td colspan="4" style="text-align:center;color:#888;">No history yet</td></tr>
                {% endif %}
            </table>
        </div>
        
        <button class="btn" onclick="killAll()">☠️ Kill All</button>
        <p class="refresh">Auto-refreshes every 2 seconds</p>
    </div>
</body>
</html>
"""


def get_status():
    """Check current device status"""
    status = {"camera": False, "microphone": False}
    
    try:
        result = subprocess.run(['fuser', '/dev/video0'], capture_output=True, text=True)
        if result.stdout.strip():
            status['camera'] = True
    except:
        pass
    
    try:
        result = subprocess.run(['fuser', '/dev/snd/pcmC0D0c'], capture_output=True, text=True)
        if result.stdout.strip():
            status['microphone'] = True
    except:
        pass
    
    return status


def get_history(limit=10):
    """Get recent access history"""
    if not os.path.exists(DB_PATH):
        return []
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT timestamp, device, process, duration 
        FROM access_log 
        WHERE duration > 0 
        ORDER BY timestamp DESC 
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows


@app.route('/')
def index():
    history = get_history()
    return render_template_string(HTML_TEMPLATE, history=history)


@app.route('/api/status')
def api_status():
    return jsonify(get_status())


@app.route('/api/kill')
def api_kill():
    subprocess.run(['fuser', '-k', '/dev/video0'])
    subprocess.run(['fuser', '-k', '/dev/snd/pcmC0D0c'])
    return jsonify({"status": "ok", "message": "All apps killed"})


@app.route('/api/history')
def api_history():
    return jsonify(get_history(20))


def main():
    print("🟢 Dot Web Panel starting on http://127.0.0.1:8080")
    app.run(host='127.0.0.1', port=8080, debug=False)


if __name__ == "__main__":
    main()
