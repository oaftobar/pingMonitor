# -*- mode: python ; coding: utf-8 -*-

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