# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

datas = [('archis_tracker/presets', 'archis_tracker/presets'), ('archis_tracker/assets', 'archis_tracker/assets'), ('archis_tracker/models', 'archis_tracker/models')]
binaries = []
hiddenimports = ['cv2']
datas += collect_data_files('qfluentwidgets')


a = Analysis(
    ['archis_tracker/main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['scipy', 'scipy.optimize', 'matplotlib', 'tkinter'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ArchisOpticalTracker',
    icon='archis_tracker/assets/app_icon.ico',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
