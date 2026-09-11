"""
Archis Optical Tracker - PyInstaller Executable Packager
Packages the Python tracking system into a standalone Windows executable.
"""
import subprocess
import sys
import os

def build():
    print("Building standalone executable with PyInstaller...")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=ArchisOpticalTracker",
        "--windowed",
        "--onefile",
        "--clean",
        "--collect-all=pyqtgraph",
        "--collect-all=PyQt6",
        "--collect-all=archis_tracker",
        "--hidden-import=scipy",
        "--hidden-import=scipy.optimize",
        "--hidden-import=cv2",
        "--add-data=archis_tracker/presets;archis_tracker/presets",
        "archis_tracker/main.py"
    ]
    res = subprocess.run(cmd)
    if res.returncode == 0:
        print("Standalone executable built successfully in dist/ArchisOpticalTracker.exe")
    else:
        print("PyInstaller build failed with return code:", res.returncode)

if __name__ == "__main__":
    build()
