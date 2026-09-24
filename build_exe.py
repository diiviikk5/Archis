"""
Archis Optical Tracker - PyInstaller Executable Packager
Packages the Python tracking system into a standalone Windows executable.
"""
import subprocess
import sys
import os

def build():
    print("Building standalone executable with PyInstaller...")
    cmd = [sys.executable, "-m", "PyInstaller",
           "ArchisOpticalTracker.spec", "--clean", "--noconfirm"]
    res = subprocess.run(cmd)
    if res.returncode == 0:
        print("Portable application built successfully in dist/ArchisTracker/")
    else:
        print("PyInstaller build failed with return code:", res.returncode)

if __name__ == "__main__":
    build()
