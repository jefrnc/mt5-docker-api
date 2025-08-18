FROM python:3.13.7-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg2 \
    software-properties-common \
    xvfb \
    x11vnc \
    novnc \
    supervisor \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

# Install Wine
RUN dpkg --add-architecture i386 && \
    wget -nc https://dl.winehq.org/wine-builds/winehq.key && \
    apt-key add winehq.key && \
    rm winehq.key && \
    echo "deb https://dl.winehq.org/wine-builds/debian/ bullseye main" > /etc/apt/sources.list.d/winehq.list && \
    apt-get update && \
    apt-get install -y --install-recommends winehq-stable && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt /tmp/requirements.txt

# Install Python packages from requirements
# Note: mt5linux is installed separately and may fail on some architectures
RUN pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt && \
    (pip install --no-cache-dir mt5linux==0.1.* || echo "Warning: mt5linux installation failed, will try MetaTrader5 package in Wine")

# Environment variables
ENV WINEPREFIX=/config/.wine
ENV WINEARCH=win64
ENV WINEDEBUG=-all
ENV DISPLAY=:1

# Create directories
RUN mkdir -p /app /config

# Copy application files
COPY src/ /app/
COPY Metatrader/ /Metatrader/

# Make scripts executable
RUN chmod +x /Metatrader/*.py 2>/dev/null || true

# Supervisor configuration
RUN mkdir -p /var/log/supervisor && \
    echo '[supervisord]\n\
nodaemon=true\n\
\n\
[program:xvfb]\n\
command=/usr/bin/Xvfb :1 -screen 0 1024x768x16\n\
autorestart=true\n\
\n\
[program:x11vnc]\n\
command=/usr/bin/x11vnc -display :1 -forever -shared -nopw\n\
autorestart=true\n\
startretries=10\n\
\n\
[program:novnc]\n\
command=websockify --web=/usr/share/novnc/ 3000 localhost:5900\n\
autorestart=true\n\
\n\
[program:mt5]\n\
command=python3 /Metatrader/start.py\n\
autorestart=true\n\
stdout_logfile=/var/log/supervisor/mt5.log\n\
stderr_logfile=/var/log/supervisor/mt5.err\n\
\n\
[program:api]\n\
command=python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000\n\
directory=/app\n\
autorestart=true\n\
stdout_logfile=/var/log/supervisor/api.log\n\
stderr_logfile=/var/log/supervisor/api.err\n\
' > /etc/supervisor/conf.d/supervisord.conf

# Expose ports
EXPOSE 3000 8000 8001

# Volume
VOLUME /config

# Set working directory
WORKDIR /app

# Start supervisor
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]