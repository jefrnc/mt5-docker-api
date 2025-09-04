#!/bin/bash

# Start Xvfb
Xvfb :1 -screen 0 1024x768x24 &
sleep 2

# Start x11vnc
x11vnc -display :1 -nopw -forever -xkb -shared -repeat &

# Start noVNC
websockify --web=/usr/share/novnc/ 3000 localhost:5900 &

# Start Wine and MT5 installation if needed
export DISPLAY=:1
if [ ! -f "/root/.wine/drive_c/Program Files/MetaTrader 5/terminal64.exe" ]; then
    echo "Installing MetaTrader 5..."
    cd /app/Metatrader
    python3 install_mt5.py
fi

# Start the FastAPI application
cd /app
uvicorn src.api.main:app --host 0.0.0.0 --port 8000