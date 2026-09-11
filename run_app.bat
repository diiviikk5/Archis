@echo off
title Archis Optical Tracker
cd /d "%~dp0"
python -m archis_tracker.main
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Application exited with error code %ERRORLEVEL%
    pause
)
