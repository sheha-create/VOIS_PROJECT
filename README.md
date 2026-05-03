# NetScan Pro - Advanced Network Port Scanner

NetScan Pro is a premium, multi-threaded TCP port scanner built with Python and CustomTkinter. It features a modern dark cybersecurity theme, real-time analytics, and advanced scanning controls.

## Features

- **Modern Dark UI** – Sleek interface with electric blue accents and animated background.
- **Multi-threaded Scanning** – Support for up to 500 concurrent threads for rapid results.
- **Risk Assessment** – Automatic risk-level categorization (Critical, High, Medium, Low) for open ports.
- **Service Identification** – Labels common services (SSH, HTTP, MySQL, etc.) automatically.
- **Live Analytics** – Real-time Ports-Per-Second (PPS) counter and progress tracking.
- **Stop & Resume** – Full control over active scans with pause and resume functionality.
- **Latency Tracking** – Measure the response time (ping) for each discovered port.
- **Scan History** – Sidebar tracking your last 5 targets for quick access.
- **Flexible Export** – Export your findings as professional CSV or JSON reports.

## Requirements

- Python 3.7 or newer
- `customtkinter`
- `Pillow`

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/sheha-create/VOIS_PROJECT.git
   cd VOIS_PROJECT
   ```

2. Install dependencies:
   ```bash
   pip install customtkinter Pillow
   ```

## Usage

Run the application:
```bash
python networkportscanner.py
```

1. Enter the **Target IP or Hostname**.
2. Set the **Port Range** and adjust the **Thread Slider** for speed.
3. Click **Radar Scan** to begin.
4. Use **Pause/Resume** or **Stop** as needed.
5. Filter results using the search bar or **Export** them once complete.

## Project Structure

```
VOIS_PROJECT/
├── networkportscanner.py   # Main application
└── README.md               # Documentation
```

## Disclaimer

Use this tool only on hosts and networks you own or have explicit permission to scan. Unauthorized port scanning may be illegal in your jurisdiction.

## License

This project is released under the [MIT License](https://opensource.org/licenses/MIT).
