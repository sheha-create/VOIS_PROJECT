import socket
import threading
import time
import queue
import sys
import json
import csv
import os
import math
import random
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk
from PIL import Image, ImageTk

# ---------------------------
# Constants & Theming
# ---------------------------
COLORS = {
    "bg_dark": "#0D1B2A",
    "bg_card": "#1B263B",
    "accent": "#00B4D8",
    "accent_hover": "#0096C7",
    "text_main": "#CAF0F8",
    "text_dim": "#90E0EF",
    "critical": "#FF4D4D",
    "high": "#FFA500",
    "medium": "#FFFF00",
    "low": "#00FF00",
    "neon_blue": "#00B4D8"
}

COMMON_PORTS = {
    21: ('FTP', 'Critical'), 22: ('SSH', 'Critical'), 23: ('Telnet', 'Critical'),
    25: ('SMTP', 'High'), 53: ('DNS', 'Medium'), 80: ('HTTP', 'High'),
    110: ('POP3', 'Medium'), 143: ('IMAP', 'Medium'), 443: ('HTTPS', 'High'),
    3306: ('MySQL', 'Critical'), 3389: ('RDP', 'Critical'), 5900: ('VNC', 'Critical'),
    8080: ('HTTP-Alt', 'High'), 20: ('FTP-Data', 'Medium'), 161: ('SNMP', 'High'),
    445: ('SMB', 'Critical'), 1433: ('MSSQL', 'Critical'), 5432: ('PostgreSQL', 'Critical')
}

# ---------------------------
# Scanner Logic
# ---------------------------
class PortScanner:
    def __init__(self, target, start_port, end_port, timeout=0.4, max_workers=100):
        self.target = target
        self.start_port = start_port
        self.end_port = end_port
        self.timeout = timeout
        self.max_workers = max_workers
        
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set() # Start unpaused
        
        self.total_ports = max(0, end_port - start_port + 1)
        self.scanned_count = 0
        self.open_ports = []
        self._lock = threading.Lock()
        self.result_queue = queue.Queue()
        self.start_time = None
        self.current_port = start_port

    def stop(self):
        self._stop_event.set()
        self._pause_event.set()

    def pause(self):
        self._pause_event.clear()

    def resume(self):
        self._pause_event.set()

    def _get_latency(self, port):
        # Basic latency estimation
        try:
            start = time.perf_counter()
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(self.timeout)
            s.connect((self.target, port))
            s.close()
            return (time.perf_counter() - start) * 1000
        except:
            return 0

    def _scan_port(self, port):
        if self._stop_event.is_set():
            return
        
        self._pause_event.wait()
        
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(self.timeout)
            result = s.connect_ex((self.target, port))
            if result == 0:
                service, risk = COMMON_PORTS.get(port, ('Unknown', 'Low'))
                latency = self._get_latency(port)
                res_data = {
                    'port': port,
                    'service': service,
                    'risk': risk,
                    'latency': f"{latency:.1f}ms" if latency > 0 else "N/A"
                }
                with self._lock:
                    self.open_ports.append(res_data)
                self.result_queue.put(('open', res_data))
            s.close()
        except Exception as e:
            pass
        finally:
            with self._lock:
                self.scanned_count += 1
            self.result_queue.put(('progress', self.scanned_count, port))

    def run(self):
        self.start_time = time.time()
        sem = threading.Semaphore(self.max_workers)
        threads = []

        for port in range(self.start_port, self.end_port + 1):
            if self._stop_event.is_set():
                break
            
            self._pause_event.wait()
            sem.acquire()
            t = threading.Thread(target=self._worker_wrapper, args=(sem, port), daemon=True)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.result_queue.put(('done', len(self.open_ports)))

    def _worker_wrapper(self, sem, port):
        try:
            self._scan_port(port)
        finally:
            sem.release()

# ---------------------------
# UI Components
# ---------------------------
class AnimatedBackground(tk.Canvas):
    def __init__(self, master, **kwargs):
        super().__init__(master, highlightthickness=0, **kwargs)
        self.particles = []
        self.n_particles = 40
        self.width = 0
        self.height = 0
        self.bind("<Configure>", self._on_resize)
        self._animate()

    def _on_resize(self, event):
        self.width = event.width
        self.height = event.height
        self._init_particles()

    def _init_particles(self):
        self.particles = []
        for _ in range(self.n_particles):
            self.particles.append({
                'x': random.randint(0, self.width),
                'y': random.randint(0, self.height),
                'vx': (random.random() - 0.5) * 0.8,
                'vy': (random.random() - 0.5) * 0.8,
                'radius': random.randint(1, 3)
            })

    def _animate(self):
        self.delete("all")
        if self.width > 0:
            # Update particles
            for p in self.particles:
                p['x'] += p['vx']
                p['y'] += p['vy']
                
                if p['x'] < 0 or p['x'] > self.width: p['vx'] *= -1
                if p['y'] < 0 or p['y'] > self.height: p['vy'] *= -1
                
                # Draw connections
                for p2 in self.particles:
                    dist = math.sqrt((p['x']-p2['x'])**2 + (p['y']-p2['y'])**2)
                    if dist < 100:
                        alpha = int(255 * (1 - dist/100) * 0.1)
                        color = f"#{alpha:02x}{alpha:02x}{alpha:02x}" # Subtle grey/blue
                        # Use a fixed color with transparency simulation
                        self.create_line(p['x'], p['y'], p2['x'], p2['y'], fill="#1B263B", width=1)
                
                self.create_oval(p['x']-p['radius'], p['y']-p['radius'], 
                                 p['x']+p['radius'], p['y']+p['radius'], 
                                 fill="#00B4D8", outline="")
        
        self.after(50, self._animate)

class NetScanPro(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("NetScan Pro - Advanced Port Scanner")
        self.geometry("1100x750")
        ctk.set_appearance_mode("dark")
        
        self.scanner = None
        self.scan_thread = None
        self.history = self._load_history()
        self.results_data = []
        self.start_time = None
        
        self._setup_ui()

    def _setup_ui(self):
        # Background
        self.bg_canvas = AnimatedBackground(self, bg=COLORS["bg_dark"])
        self.bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        
        # Main Container
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Header
        self._build_header()
        
        # Top Section: Settings
        self._build_settings_card()
        
        # Mid Section: Status
        self._build_status_card()
        
        # Bottom Section: Two Columns
        self.bottom_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.bottom_frame.pack(fill="both", expand=True, pady=(10, 0))
        
        self._build_results_panel()
        self._build_history_sidebar()
        
        # Footer
        self._build_footer()

    def _build_header(self):
        header = ctk.CTkFrame(self.main_container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 10))
        
        # Logo placeholder (Shield)
        self.logo_canvas = tk.Canvas(header, width=40, height=40, bg=COLORS["bg_dark"], highlightthickness=0)
        self.logo_canvas.pack(side="left")
        self._draw_shield(self.logo_canvas)
        
        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left", padx=10)
        
        ctk.CTkLabel(title_frame, text="NETSCAN PRO", font=("Impact", 24), text_color=COLORS["accent"]).pack(side="top", anchor="w")
        ctk.CTkLabel(title_frame, text="v2.0 Enterprise Edition", font=("Consolas", 10), text_color=COLORS["text_dim"]).pack(side="top", anchor="w")
        
        self.theme_toggle = ctk.CTkSwitch(header, text="Dark Mode", command=self._toggle_theme, progress_color=COLORS["accent"])
        self.theme_toggle.select()
        self.theme_toggle.pack(side="right")

    def _draw_shield(self, canvas):
        canvas.create_polygon([20, 5, 35, 10, 35, 25, 20, 38, 5, 25, 5, 10], fill=COLORS["accent"], outline="white")
        canvas.create_line(20, 8, 20, 35, fill="white", width=2)

    def _build_settings_card(self):
        card = ctk.CTkFrame(self.main_container, fg_color=COLORS["bg_card"], corner_radius=15, border_width=1, border_color=COLORS["accent"])
        card.pack(fill="x", pady=10)
        
        # Grid layout
        card.grid_columnconfigure((0,1,2,3), weight=1)
        
        # Target
        ctk.CTkLabel(card, text="Target IP / Host:", font=("JetBrains Mono", 12)).grid(row=0, column=0, padx=15, pady=(15, 0), sticky="w")
        self.ent_target = ctk.CTkEntry(card, placeholder_text="192.168.1.1", width=250, fg_color=COLORS["bg_dark"], border_color=COLORS["accent"])
        self.ent_target.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="w")
        
        # Ports
        ctk.CTkLabel(card, text="Port Range (Start - End):", font=("JetBrains Mono", 12)).grid(row=0, column=1, padx=15, pady=(15, 0), sticky="w")
        port_frame = ctk.CTkFrame(card, fg_color="transparent")
        port_frame.grid(row=1, column=1, padx=15, pady=(0, 15), sticky="w")
        
        self.ent_start = ctk.CTkEntry(port_frame, width=80, fg_color=COLORS["bg_dark"], border_color=COLORS["accent"])
        self.ent_start.insert(0, "1")
        self.ent_start.pack(side="left")
        ctk.CTkLabel(port_frame, text=" - ").pack(side="left")
        self.ent_end = ctk.CTkEntry(port_frame, width=80, fg_color=COLORS["bg_dark"], border_color=COLORS["accent"])
        self.ent_end.insert(0, "1024")
        self.ent_end.pack(side="left")
        
        # Threads
        ctk.CTkLabel(card, text="Threads (Scanning Speed):", font=("JetBrains Mono", 12)).grid(row=0, column=2, padx=15, pady=(15, 0), sticky="w")
        self.thread_slider = ctk.CTkSlider(card, from_=1, to=500, number_of_steps=499, command=self._update_thread_label, progress_color=COLORS["accent"])
        self.thread_slider.set(100)
        self.thread_slider.grid(row=1, column=2, padx=15, pady=(0, 15), sticky="ew")
        self.lbl_threads = ctk.CTkLabel(card, text="100 Threads", font=("JetBrains Mono", 10))
        self.lbl_threads.grid(row=2, column=2, padx=15, pady=(0, 5), sticky="e")
        
        # Buttons
        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.grid(row=0, column=3, rowspan=3, padx=15, pady=15, sticky="nsew")
        
        self.btn_start = ctk.CTkButton(btn_frame, text="RADAR SCAN", font=("Impact", 18), fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], command=self.start_scan)
        self.btn_start.pack(fill="x", pady=5)
        
        sub_btn_frame = ctk.CTkFrame(btn_frame, fg_color="transparent")
        sub_btn_frame.pack(fill="x")
        
        self.btn_stop = ctk.CTkButton(sub_btn_frame, text="STOP", width=70, fg_color="#660000", hover_color="#990000", state="disabled", command=self.stop_scan)
        self.btn_stop.pack(side="left", expand=True, padx=(0, 2))
        
        self.btn_pause = ctk.CTkButton(sub_btn_frame, text="PAUSE", width=70, fg_color="#444", state="disabled", command=self.toggle_pause)
        self.btn_pause.pack(side="left", expand=True, padx=(2, 0))

    def _build_status_card(self):
        card = ctk.CTkFrame(self.main_container, fg_color=COLORS["bg_card"], corner_radius=15, border_width=1, border_color="#333")
        card.pack(fill="x", pady=10)
        
        self.progress_bar = ctk.CTkProgressBar(card, progress_color=COLORS["accent"])
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=20, pady=(15, 5))
        
        stats_frame = ctk.CTkFrame(card, fg_color="transparent")
        stats_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        self.lbl_pct = ctk.CTkLabel(stats_frame, text="0%", font=("JetBrains Mono", 14, "bold"), text_color=COLORS["accent"])
        self.lbl_pct.pack(side="left")
        
        self.lbl_pps = ctk.CTkLabel(stats_frame, text="0 ports/sec", font=("JetBrains Mono", 12))
        self.lbl_pps.pack(side="left", padx=20)
        
        self.lbl_current_port = ctk.CTkLabel(stats_frame, text="Idle", font=("JetBrains Mono", 12), text_color=COLORS["text_dim"])
        self.lbl_current_port.pack(side="right")
        
        self.lbl_timer = ctk.CTkLabel(stats_frame, text="Elapsed: 0s", font=("JetBrains Mono", 12))
        self.lbl_timer.pack(side="right", padx=20)

    def _build_results_panel(self):
        panel = ctk.CTkFrame(self.bottom_frame, fg_color=COLORS["bg_card"], corner_radius=15, border_width=1, border_color="#333")
        panel.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        # Toolbar
        toolbar = ctk.CTkFrame(panel, fg_color="transparent")
        toolbar.pack(fill="x", padx=15, pady=10)
        
        ctk.CTkLabel(toolbar, text="OPEN PORTS", font=("JetBrains Mono", 14, "bold")).pack(side="left")
        
        self.ent_search = ctk.CTkEntry(toolbar, placeholder_text="Search port or service...", width=200, height=28, fg_color=COLORS["bg_dark"])
        self.ent_search.pack(side="right", padx=5)
        self.ent_search.bind("<KeyRelease>", self._filter_results)
        
        # Header for the list
        list_header = ctk.CTkFrame(panel, fg_color="#222", height=30)
        list_header.pack(fill="x")
        ctk.CTkLabel(list_header, text="PORT", width=80).pack(side="left", padx=10)
        ctk.CTkLabel(list_header, text="SERVICE", width=120).pack(side="left", padx=10)
        ctk.CTkLabel(list_header, text="RISK LEVEL", width=120).pack(side="left", padx=10)
        ctk.CTkLabel(list_header, text="LATENCY").pack(side="left", padx=10)
        
        # Results List (Scrollable)
        self.results_list = ctk.CTkScrollableFrame(panel, fg_color=COLORS["bg_dark"], corner_radius=0)
        self.results_list.pack(fill="both", expand=True, padx=1, pady=(0, 1))

    def _build_history_sidebar(self):
        sidebar = ctk.CTkFrame(self.bottom_frame, fg_color=COLORS["bg_card"], corner_radius=15, width=250, border_width=1, border_color="#333")
        sidebar.pack(side="right", fill="y", padx=(10, 0))
        sidebar.pack_propagate(False)
        
        ctk.CTkLabel(sidebar, text="SCAN HISTORY", font=("JetBrains Mono", 14, "bold")).pack(pady=10)
        
        self.history_list = ctk.CTkScrollableFrame(sidebar, fg_color="transparent")
        self.history_list.pack(fill="both", expand=True)
        
        self._refresh_history_ui()

    def _build_footer(self):
        footer = ctk.CTkFrame(self.main_container, fg_color="transparent")
        footer.pack(fill="x", pady=10)
        
        self.lbl_summary = ctk.CTkLabel(footer, text="Ready to scan. Select a target and press Radar Scan.", font=("JetBrains Mono", 11))
        self.lbl_summary.pack(side="left")
        
        self.btn_export = ctk.CTkButton(footer, text="EXPORT RESULTS", width=120, height=32, fg_color="#333", border_width=1, border_color=COLORS["accent"], state="disabled", command=self.export_results)
        self.btn_export.pack(side="right")

    # -----------------------
    # Handlers
    # -----------------------
    def _update_thread_label(self, val):
        self.lbl_threads.configure(text=f"{int(val)} Threads")

    def _toggle_theme(self):
        mode = "dark" if self.theme_toggle.get() else "light"
        ctk.set_appearance_mode(mode)

    def start_scan(self):
        target = self.ent_target.get().strip()
        if not target:
            messagebox.showerror("Error", "Please enter a target.")
            return
        
        try:
            start_p = int(self.ent_start.get())
            end_p = int(self.ent_end.get())
            threads = int(self.thread_slider.get())
        except:
            messagebox.showerror("Error", "Invalid port range or thread count.")
            return

        # UI Reset
        for widget in self.results_list.winfo_children():
            widget.destroy()
        
        self.results_data = []
        self.progress_bar.set(0)
        self.lbl_pct.configure(text="0%")
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.btn_pause.configure(state="normal", text="PAUSE")
        self.btn_export.configure(state="disabled")
        
        self.scanner = PortScanner(target, start_p, end_p, max_workers=threads)
        
        self.start_time = time.time()
        self.scan_thread = threading.Thread(target=self.scanner.run, daemon=True)
        self.scan_thread.start()
        
        self._save_to_history(target)
        self._refresh_history_ui()
        
        self._poll_results()
        self._update_stats_loop()

    def stop_scan(self):
        if self.scanner:
            self.scanner.stop()
            self.show_toast("Stopping scan...")

    def toggle_pause(self):
        if not self.scanner: return
        if self.btn_pause.cget("text") == "PAUSE":
            self.scanner.pause()
            self.btn_pause.configure(text="RESUME", fg_color=COLORS["accent"])
            self.show_toast("Scan Paused")
        else:
            self.scanner.resume()
            self.btn_pause.configure(text="PAUSE", fg_color="#444")
            self.show_toast("Scan Resumed")

    def _poll_results(self):
        if not self.scanner: return
        
        try:
            while True:
                msg = self.scanner.result_queue.get_nowait()
                mtype = msg[0]
                
                if mtype == 'open':
                    data = msg[1]
                    self.results_data.append(data)
                    self._add_result_row(data)
                elif mtype == 'progress':
                    count, current = msg[1], msg[2]
                    pct = count / self.scanner.total_ports
                    self.progress_bar.set(pct)
                    self.lbl_pct.configure(text=f"{int(pct*100)}%")
                    self.lbl_current_port.configure(text=f"Scanning: {current}")
                elif mtype == 'done':
                    self._finalize_scan(msg[1])
                    return
        except queue.Empty:
            pass
        
        if self.scan_thread.is_alive():
            self.after(50, self._poll_results)

    def _update_stats_loop(self):
        if self.scanner and self.scan_thread.is_alive():
            elapsed = time.time() - self.start_time
            self.lbl_timer.configure(text=f"Elapsed: {int(elapsed)}s")
            
            if elapsed > 0:
                pps = self.scanner.scanned_count / elapsed
                self.lbl_pps.configure(text=f"{int(pps)} ports/sec")
            
            self.after(1000, self._update_stats_loop)

    def _add_result_row(self, data):
        row = ctk.CTkFrame(self.results_list, fg_color="transparent")
        row.pack(fill="x", pady=2)
        
        risk_color = COLORS.get(data['risk'].lower(), COLORS["text_main"])
        
        ctk.CTkLabel(row, text=data['port'], width=80, font=("JetBrains Mono", 12, "bold")).pack(side="left", padx=10)
        ctk.CTkLabel(row, text=data['service'], width=120).pack(side="left", padx=10)
        
        badge = ctk.CTkFrame(row, fg_color=risk_color, width=100, height=20, corner_radius=10)
        badge.pack(side="left", padx=10)
        badge.pack_propagate(False)
        ctk.CTkLabel(badge, text=data['risk'].upper(), text_color="black", font=("Arial", 10, "bold")).pack()
        
        ctk.CTkLabel(row, text=data['latency']).pack(side="left", padx=10)

    def _finalize_scan(self, count):
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.btn_pause.configure(state="disabled")
        self.btn_export.configure(state="normal")
        self.lbl_summary.configure(text=f"Scan Complete: {count} open ports found.")
        self.show_toast(f"Scan complete — {count} open ports found")

    def _filter_results(self, event=None):
        query = self.ent_search.get().lower()
        for child in self.results_list.winfo_children():
            child.destroy()
        
        for data in self.results_data:
            if query in str(data['port']) or query in data['service'].lower():
                self._add_result_row(data)

    # -----------------------
    # History & Persistence
    # -----------------------
    def _load_history(self):
        try:
            if os.path.exists("scan_history.json"):
                with open("scan_history.json", "r") as f:
                    return json.load(f)
        except: pass
        return []

    def _save_to_history(self, target):
        entry = {
            "target": target,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        self.history.insert(0, entry)
        self.history = self.history[:5] # Keep last 5
        try:
            with open("scan_history.json", "w") as f:
                json.dump(self.history, f)
        except: pass

    def _refresh_history_ui(self):
        for widget in self.history_list.winfo_children():
            widget.destroy()
        
        for entry in self.history:
            item = ctk.CTkFrame(self.history_list, fg_color="#222", corner_radius=8)
            item.pack(fill="x", pady=5, padx=5)
            ctk.CTkLabel(item, text=entry["target"], font=("JetBrains Mono", 11, "bold")).pack(pady=(5, 0))
            ctk.CTkLabel(item, text=entry["timestamp"], font=("JetBrains Mono", 9), text_color="#777").pack(pady=(0, 5))

    # -----------------------
    # Export & Notifications
    # -----------------------
    def export_results(self):
        if not self.results_data: return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("CSV", "*.csv")]
        )
        if not file_path: return
        
        try:
            if file_path.endswith(".json"):
                with open(file_path, "w") as f:
                    json.dump(self.results_data, f, indent=4)
            else:
                keys = self.results_data[0].keys()
                with open(file_path, "w", newline="") as f:
                    dict_writer = csv.DictWriter(f, keys)
                    dict_writer.writeheader()
                    dict_writer.writerows(self.results_data)
            messagebox.showinfo("Export", f"Results exported to {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export: {e}")

    def show_toast(self, message):
        toast = ctk.CTkToplevel(self)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        
        # Position toast
        x = self.winfo_x() + self.winfo_width()//2 - 150
        y = self.winfo_y() + 50
        toast.geometry(f"300x40+{x}+{y}")
        
        frame = ctk.CTkFrame(toast, fg_color=COLORS["accent"], corner_radius=10)
        frame.pack(fill="both", expand=True)
        ctk.CTkLabel(frame, text=message, text_color="black", font=("JetBrains Mono", 11, "bold")).pack(pady=10)
        
        self.after(2500, toast.destroy)

if __name__ == "__main__":
    app = NetScanPro()
    app.mainloop()
