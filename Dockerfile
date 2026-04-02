FROM python:3.13-slim-bookworm

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
    lsb-release \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Wine (updated for Bookworm)
RUN dpkg --add-architecture i386 && \
    mkdir -pm755 /etc/apt/keyrings && \
    wget -O /etc/apt/keyrings/winehq-archive.key https://dl.winehq.org/wine-builds/winehq.key && \
    wget -NP /etc/apt/sources.list.d/ https://dl.winehq.org/wine-builds/debian/dists/bookworm/winehq-bookworm.sources && \
    apt-get update && \
    apt-get install -y --install-recommends winehq-stable && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt /tmp/requirements.txt

# Install Python packages from requirements
RUN pip install --no-cache-dir -r /tmp/requirements.txt || true

# Create working directory
WORKDIR /app

# Copy application code
COPY . /app/

# Set environment variables
ENV DISPLAY=:1
ENV PYTHONUNBUFFERED=1
ENV WINEPREFIX=/root/.wine

# Configure Wine
RUN winecfg || true

# Expose ports
EXPOSE 5900 6080 8000

# Make entrypoint script executable
RUN chmod +x /app/scripts/entrypoint.sh

CMD ["/app/scripts/entrypoint.sh"]
