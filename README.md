# Ping Monitor

A minimal, junior-friendly network device monitor that pings devices and tracks their online status and latency.

## Description

Ping Monitor is a cross-platform desktop application that monitors network devices by pinging them at configurable intervals. It's designed to be simple to understand and easy to modify for new developers.

## Features

- **Device Management**: Add, remove, and organize network devices by IP address
- **Live Monitoring**: Real-time ping results with status indicators (green = online, red = offline)
- **Configurable Intervals**: Choose between 10 seconds, 60 seconds, or 5 minutes
- **Latency Tracking**: Display response time in milliseconds
- **Ping History**: View historical ping data per device with uptime statistics
- **Import/Export**: Backup and share device lists via JSON files
- **Keyboard Shortcuts**: Quick actions for faster workflow
- **Auto-Updates**: Check for new versions with one click

## Downloads

Download the latest release from [GitHub Releases](https://github.com/oaftobar/pingMonitor/releases):

| Platform | File |
|----------|------|
| Windows | `PingMonitor.exe` |
| macOS | `PingMonitor.app` |
| Linux | `PingMonitor` |

## Getting Started

### Run from Source

Requirements:
- Python 3.9+
- Tkinter (included with most Python installations)

```bash
python3 pingMonitor.py
```

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Enter | Add device (when in IP field) |
| Escape | Clear input fields |
| Cmd/Ctrl + W | Close window |
| Cmd/Ctrl + Q | Quit application |

## Usage

### Adding Devices
1. Enter a device name (e.g., "Office Printer")
2. Enter the IP address (e.g., "192.168.1.100")
3. Click "Add Device" or press Enter

### Viewing History
- Click "History" next to any device to see:
  - Total pings and uptime percentage
  - Average, minimum, and maximum latency
  - Last 10 ping results

### Import/Export Devices
- **File → Export Devices**: Save your device list to a JSON file
- **File → Import Devices**: Load devices from a JSON file

### Ping Intervals
- 10 seconds: Fast checking for lab environments
- 60 seconds: Moderate checking with less traffic
- 5 minutes: Slow checking for critical devices

## File Structure

```
pingMonitor/
├── pingMonitor.py       # Main application
├── ping_service.py      # Ping functionality
├── devices.json         # Saved devices (created automatically)
├── devices.example.json # Example device configuration
├── pingMonitorICON.png # Application icon
└── README.md           # This file
```

## Development

### Building Executables

Use PyInstaller to create standalone executables:

```bash
pip install pyinstaller Pillow
pyinstaller --onefile --windowed --name PingMonitor pingMonitor.py
```

### Checking for Updates

Help → Check for Updates to see if a new version is available.

## Version History

- **0.3.2**: Fix GitHub link, add Cmd+W shortcut
- **0.3.1**: Check for Updates feature
- **0.3.0**: Keyboard shortcuts and ping history
- **0.2.x**: Bug fixes and code improvements
- **0.1.0**: Initial release

## License

MIT License

## Author

Developed by Brennan Wade
