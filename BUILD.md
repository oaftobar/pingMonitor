# Build Instructions for PingMonitor

This document explains how to build PingMonitor executables for different platforms.

## Quick Start

### macOS (Apple Silicon/Intel)
```bash
python3 build.py
```
This creates:
- `dist/PingMonitor.app` - macOS application bundle
- `dist/PingMonitor` - Standalone executable

### Windows
Run the batch file:
```cmd
build_windows.bat
```
This creates:
- `dist/PingMonitor.exe` - Windows executable

## Manual Build Instructions

### Prerequisites
- Python 3.8+
- Tkinter (included with most Python installations)

### Step 1: Set up virtual environment
```bash
# macOS/Linux
python3 -m venv packaging_env
source packaging_env/bin/activate

# Windows
python -m venv packaging_env
packaging_env\Scripts\activate
```

### Step 2: Install dependencies
```bash
pip install pyinstaller Pillow
```

### Step 3: Build executable
```bash
pyinstaller pingMonitor.spec
```

## Output Files

### macOS
- **PingMonitor.app**: Double-click to launch, includes app icon
- **PingMonitor**: Command-line executable

### Windows
- **PingMonitor.exe**: Windows GUI executable with icon

## Distribution Notes

### macOS
- The .app bundle is self-contained and doesn't require Python installation
- Standalone executable works on both Apple Silicon and Intel Macs
- Gatekeeper may show security warning on first launch - right-click and "Open"

### Windows
- The .exe is self-contained and doesn't require Python installation
- Windows Defender may flag unknown executables - this is normal
- No installation required - just copy and run

## Troubleshooting

### Common Issues
1. **ModuleNotFoundError**: Make sure all dependencies are installed
2. **Icon not loading**: Ensure `pingMonitorICON.png` exists in the same directory
3. **Permission denied**: Make sure the executable has execution permissions

### Rebuilding
To clean and rebuild:
```bash
rm -rf dist build
pyinstaller pingMonitor.spec
```

## File Structure After Build
```
pingMonitor/
├── dist/
│   ├── PingMonitor.app/          # macOS app bundle
│   └── PingMonitor               # Standalone executable
├── build/                        # Build artifacts (can be deleted)
├── packaging_env/               # Virtual environment
└── pingMonitor.spec             # PyInstaller configuration
```