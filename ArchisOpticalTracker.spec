# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = [
    ('archis_tracker/presets', 'archis_tracker/presets'),
    ('archis_tracker/assets', 'archis_tracker/assets'),
    ('archis_tracker/models', 'archis_tracker/models'),
    ('scenarios', 'scenarios'),
]
datas += collect_data_files('qfluentwidgets')
hiddenimports = ['cv2'] + collect_submodules('qfluentwidgets')

a = Analysis(
    ['archis_tracker/main.py'], pathex=[], binaries=[], datas=datas,
    hiddenimports=hiddenimports, hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=['scipy', 'matplotlib', 'tkinter'], noarchive=False, optimize=1,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True,
    name='ArchisTracker', icon='archis_tracker/assets/app_icon.ico',
    debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
    console=False, disable_windowed_traceback=False,
)
coll = COLLECT(
    exe, a.binaries, a.datas, strip=False, upx=False,
    name='ArchisTracker',
)
