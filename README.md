# Ping Monitor

Foundation: a minimal, junior-friendly monitor that inputs a known IP with a name and monitors its reachability via pings.

What this app does
- UI to input a device name and IP address
- Shows a live list with Name, IP, Status, Latency, Actions
- Background ping runs at a configurable interval (10 sec, 60 sec, 5 min); Status color: green = Online, red = Offline
- Persists devices to devices.json across sessions
- Can be pre-populated by copying devices.example.json to devices.json and editing it
- Very small and easy to understand for new developers

Getting started
- Requirements: Python 3.x; Tkinter is included with standard Python installations on most platforms.
- Run the monitor:
  - python3 pingMonitor.py
- Add devices: In the UI, enter Name and IP, then click Add Device.
- Set ping interval: Select an interval from the dropdown and click Apply.
- Status updates: Online (green) when a device responds to a ping, Offline (red) when it does not.
- Latency updates: shows ms for online devices.
- Remove devices: Click Remove in the Actions column.
- Devices are saved to devices.json. Copy devices.example.json to devices.json and edit to pre-populate your list.

Ping interval options
- 10 seconds (default): fast checking for lab environments.
- 60 seconds: moderate checking with less frequent traffic.
- 5 minutes: slow checking for less critical devices or when minimizing network load.
- To change: select an interval, then click Apply.

About
- Version: 0.1.0-beta
- Use the Help → About dialog to view version and info.

Notes
- This is intentionally minimal and designed for quick validation with real devices.
- Edit devices.json to add permanent devices; the app loads it on startup and updates it when you add/remove via UI.
- You can delete devices.json to start fresh.