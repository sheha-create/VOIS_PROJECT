import socket
import threading
import time
import os
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'netscan_pro_secret'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# ---------------------------
# Port Scanner Logic (Web)
# ---------------------------
COMMON_PORTS = {
    21: ('FTP', 'Critical'), 22: ('SSH', 'Critical'), 23: ('Telnet', 'Critical'),
    25: ('SMTP', 'High'), 53: ('DNS', 'Medium'), 80: ('HTTP', 'High'),
    110: ('POP3', 'Medium'), 143: ('IMAP', 'Medium'), 443: ('HTTPS', 'High'),
    3306: ('MySQL', 'Critical'), 3389: ('RDP', 'Critical'), 5900: ('VNC', 'Critical'),
    8080: ('HTTP-Alt', 'High'), 445: ('SMB', 'Critical')
}

active_scans = {}

class WebPortScanner:
    def __init__(self, sid, target, start_port, end_port, timeout=0.4, max_workers=100):
        self.sid = sid
        self.target = target
        self.start_port = start_port
        self.end_port = end_port
        self.timeout = timeout
        self.max_workers = max_workers
        self._stop_event = threading.Event()
        self.scanned_count = 0
        self.total_ports = max(0, end_port - start_port + 1)
        self.start_time = None

    def stop(self):
        self._stop_event.set()

    def _get_latency(self, port):
        try:
            start = time.perf_counter()
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(self.timeout)
            s.connect((self.target, port))
            s.close()
            return (time.perf_counter() - start) * 1000
        except: return 0

    def scan(self):
        self.start_time = time.time()
        sem = threading.Semaphore(self.max_workers)
        threads = []

        for port in range(self.start_port, self.end_port + 1):
            if self._stop_event.is_set(): break
            sem.acquire()
            t = threading.Thread(target=self._scan_worker, args=(sem, port), daemon=True)
            threads.append(t)
            t.start()

        for t in threads: t.join()
        socketio.emit('scan_complete', {'total_open': self.scanned_count}, room=self.sid)

    def _scan_worker(self, sem, port):
        try:
            if not self._stop_event.is_set():
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(self.timeout)
                if s.connect_ex((self.target, port)) == 0:
                    service, risk = COMMON_PORTS.get(port, ('Unknown', 'Low'))
                    latency = self._get_latency(port)
                    socketio.emit('port_found', {
                        'port': port,
                        'service': service,
                        'risk': risk,
                        'latency': f"{latency:.1f}ms" if latency > 0 else "N/A"
                    }, room=self.sid)
                s.close()
        finally:
            self.scanned_count += 1
            progress = (self.scanned_count / self.total_ports) * 100
            socketio.emit('progress', {
                'percent': int(progress),
                'current_port': port,
                'scanned': self.scanned_count,
                'total': self.total_ports
            }, room=self.sid)
            sem.release()

# ---------------------------
# Flask Routes
# ---------------------------
@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('start_scan')
def handle_start_scan(data):
    sid = request.sid
    target = data.get('target')
    start_port = int(data.get('start_port', 1))
    end_port = int(data.get('end_port', 1024))
    threads = int(data.get('threads', 100))

    if sid in active_scans:
        active_scans[sid].stop()

    scanner = WebPortScanner(sid, target, start_port, end_port, max_workers=threads)
    active_scans[sid] = scanner
    
    # Run scanner in background thread
    socketio.start_background_task(scanner.scan)

@socketio.on('stop_scan')
def handle_stop_scan():
    sid = request.sid
    if sid in active_scans:
        active_scans[sid].stop()
        del active_scans[sid]

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    if sid in active_scans:
        active_scans[sid].stop()
        del active_scans[sid]

if __name__ == '__main__':
    socketio.run(app, debug=True)
