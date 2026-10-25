@echo off
title Donnie Offline Astrology Engine
color 0A
cls
echo ========================================================
echo        DONNIE ASTROLOGY ENGINE - OFFLINE SERVER
echo ========================================================
echo.
echo  [STATUS] Starting Local Swiss Ephemeris Server...
echo  [URL]    http://127.0.0.1:5000
echo.
echo  Keep this small window minimized while using the app.
echo  Close this window whenever you are done!
echo ========================================================
echo.
python app.py
pause