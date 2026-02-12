#!/usr/bin/env python3
"""
Build script for PingMonitor executables
This script packages PingMonitor for different platforms:
- macOS: .app bundle and standalone executable
- Windows: .exe executable (run on Windows)
"""

import os
import platform
import subprocess
import sys
from pathlib import Path


def install_dependencies():
    """Install required dependencies in virtual environment"""
    print("Installing dependencies...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "pyinstaller", "Pillow"], check=True
    )


def create_spec_file():
    """Create the PyInstaller spec file if it doesn't exist"""
    spec_content = """# -*- mode: python ; coding: utf-8 -*-

import os
import platform

block_cipher = None

# Determine the platform-specific settings
is_windows = platform.system().lower() == 'windows'
is_macos = platform.system().lower() == 'darwin'

# Data files to include
datas = [
    ('devices.example.json', '.'),
    ('pingMonitorICON.png', '.'),
]

# For Windows, include additional files if needed
if is_windows:
    pass

a = Analysis(
    ['pingMonitor.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PingMonitor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to False for GUI app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='pingMonitorICON.png' if os.path.exists('pingMonitorICON.png') else None,
)

# For macOS, create an app bundle
if is_macos:
    app = BUNDLE(
        exe,
        name='PingMonitor.app',
        icon='pingMonitorICON.png' if os.path.exists('pingMonitorICON.png') else None,
        bundle_identifier='com.wade.pingmonitor',
        info_plist={
            'CFBundleName': 'Ping Monitor',
            'CFBundleDisplayName': 'Ping Monitor',
            'CFBundleVersion': '0.1.0',
            'CFBundleShortVersionString': '0.1.0-beta',
            'CFBundleIdentifier': 'com.wade.pingmonitor',
            'NSHighResolutionCapable': True,
        },
    )
"""

    if not os.path.exists("pingMonitor.spec"):
        with open("pingMonitor.spec", "w") as f:
            f.write(spec_content)
        print("Created pingMonitor.spec")
    else:
        print("pingMonitor.spec already exists")


def build_executable():
    """Build the executable using PyInstaller"""
    print("Building executable...")

    # Clean previous builds
    for path in ["dist", "build"]:
        if os.path.exists(path):
            subprocess.run(["rm", "-rf", path], check=False)

    # Run PyInstaller
    subprocess.run(["pyinstaller", "pingMonitor.spec"], check=True)

    print(f"Build complete! Check the 'dist' directory for executables.")

    # List built files
    if os.path.exists("dist"):
        print("\nBuilt files:")
        for item in os.listdir("dist"):
            item_path = os.path.join("dist", item)
            if os.path.isfile(item_path):
                size = os.path.getsize(item_path) / (1024 * 1024)  # MB
                print(f"  {item} ({size:.1f} MB)")
            else:
                print(f"  {item}/")


def main():
    """Main build process"""
    print(f"Building PingMonitor for {platform.system()}...")

    # Install dependencies
    install_dependencies()

    # Create spec file
    create_spec_file()

    # Build executable
    build_executable()

    # Platform-specific instructions
    current_platform = platform.system().lower()

    if current_platform == "darwin":
        print("\n✅ macOS build complete!")
        print("Files created in dist/:")
        print("  - PingMonitor.app (macOS application bundle)")
        print("  - PingMonitor (standalone executable)")

    elif current_platform == "windows":
        print("\n✅ Windows build complete!")
        print("Files created in dist/:")
        print("  - PingMonitor.exe (Windows executable)")

    else:
        print(f"\n✅ Build complete for {current_platform}!")
        print("Check the dist/ directory for executable files.")


if __name__ == "__main__":
    main()
