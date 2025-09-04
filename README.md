# MetaTrader5 Docker API

[![Docker Build](https://github.com/jefrnc/mt5-docker-api/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/jefrnc/mt5-docker-api/actions/workflows/docker-publish.yml)
[![Docker Pulls](https://img.shields.io/docker/pulls/jsfrnc/mt5-docker-api)](https://hub.docker.com/r/jsfrnc/mt5-docker-api)
[![Docker Image Size](https://img.shields.io/docker/image-size/jsfrnc/mt5-docker-api)](https://hub.docker.com/r/jsfrnc/mt5-docker-api)
[![License](https://img.shields.io/github/license/jefrnc/mt5-docker-api)](LICENSE.md)

A containerized solution for running MetaTrader5 trading platform with web-based VNC access and Python API support.

## 🐳 Docker Hub

The official image is available on Docker Hub:

**Repository:** [jsfrnc/mt5-docker-api](https://hub.docker.com/r/jsfrnc/mt5-docker-api)

```bash
docker pull jsfrnc/mt5-docker-api:latest
```

## Overview

This Docker image allows you to run MetaTrader5 on any system that supports Docker, providing:
- Web-based access through VNC (no VNC client needed)
- Python API for algorithmic trading
- Persistent storage for configurations and data
- Automated installation and setup

## Features

- **Cross-Platform**: Run Windows-only MT5 on Linux/Mac systems
- **Web Access**: Access MT5 through any web browser on port 3000
- **Python Integration**: Built-in support for automated trading via Python
- **Auto-Installation**: MT5 installs automatically on first run
- **Persistent Data**: All settings and data persist across container restarts
- **Health Monitoring**: Built-in health checks for reliability
- **Optimized Performance**: Multi-stage build for smaller image size

## Quick Start

### Option 1: Using Docker Hub Image (Easiest)

Pull and run the latest image from Docker Hub:

```bash
# Pull the latest image
docker pull jsfrnc/mt5-docker-api:latest

# Run the container
docker run -d \
  --name mt5-docker \
  -p 3000:3000 \
  -p 8000:8000 \
  -p 8001:8001 \
  -e VNC_PASSWORD=yourpassword \
  -v mt5_data:/root/.wine/drive_c/Program\ Files/MetaTrader\ 5 \
  jsfrnc/mt5-docker-api:latest
```

Available tags:
- `jsfrnc/mt5-docker-api:latest` - Latest stable version
- `jsfrnc/mt5-docker-api:v1.0.2` - Specific version

### Option 2: Using Docker Compose (Recommended for Production)

1. Create a project directory:
```bash
mkdir mt5-docker && cd mt5-docker
```

2. Download required files:
```bash
wget https://raw.githubusercontent.com/jefrnc/mt5-docker-api/main/docker-compose.yml
wget https://raw.githubusercontent.com/jefrnc/mt5-docker-api/main/.env.example
```

3. Configure environment:
```bash
cp .env.example .env
nano .env  # Edit with your settings
```

4. Start the container:
```bash
docker compose up -d
```

The image `jsfrnc/mt5-docker-api:latest` will be automatically pulled from Docker Hub.

5. Access MetaTrader5:
   - Open your browser and navigate to `http://localhost:3000`
   - Login with the credentials you set in `.env`
   - API documentation available at `http://localhost:8000/docs`

### Using Docker CLI

```bash
docker run -d \
  -p 3000:3000 \
  -p 8000:8000 \
  -p 8001:8001 \
  -v mt5_config:/config \
  -e CUSTOM_USER=trader \
  -e PASSWORD=your_secure_password \
  jsfrnc/mt5-docker-api:latest
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CUSTOM_USER` | Yes | - | VNC username |
| `PASSWORD` | Yes | - | VNC password (min 8 chars) |
| `VNC_PORT` | No | 3000 | Web VNC interface port |
| `API_PORT` | No | 8000 | REST API server port |
| `MT5_PORT` | No | 8001 | Python MT5 server port |
| `MT5_VERSION` | No | 5.0.36 | MetaTrader5 Python library version |
| `WINE_VERSION` | No | win10 | Wine compatibility mode |
| `LOG_LEVEL` | No | INFO | Logging verbosity |

### Volume Mounts

- `/config`: Persistent storage for MT5 data, Wine prefix, and configurations

## API Usage

### REST API

The container includes a REST API with automatic documentation:

- **API Documentation**: http://localhost:8000/docs
- **OpenAPI Schema**: http://localhost:8000/openapi.json

#### Example API Calls:

```bash
# Get account info
curl http://localhost:8000/account

# Get available symbols
curl http://localhost:8000/symbols

# Get symbol details
curl http://localhost:8000/symbol/EURUSD

# Place an order
curl -X POST http://localhost:8000/order \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "EURUSD",
    "volume": 0.01,
    "order_type": "BUY"
  }'

# Get open positions
curl http://localhost:8000/positions

# Get historical data
curl -X POST http://localhost:8000/history/candles \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "EURUSD",
    "timeframe": "M5",
    "start": "2024-01-01T00:00:00",
    "end": "2024-01-02T00:00:00"
  }'
```

### WebSocket for Real-time Data

```javascript
// Connect to real-time tick stream
const ws = new WebSocket('ws://localhost:8000/ws/ticks/EURUSD');

ws.onmessage = (event) => {
  const tick = JSON.parse(event.data);
  console.log(`${tick.symbol}: Bid=${tick.bid}, Ask=${tick.ask}`);
};
```

### Python Direct Connection

You can also connect directly to MT5 without the REST API:

```python
from mt5linux import MetaTrader5

# Connect to the container
mt5 = MetaTrader5(host='localhost', port=8001)
mt5.initialize()

# Check version
print(mt5.version())

# Your trading logic here
```

## MQL5 Scripts Location

Place your Expert Advisors and Scripts in:
```
./config/.wine/drive_c/Program Files/MetaTrader 5/MQL5/
```

Access MetaEditor through the MT5 interface for development.

## Building from Source

1. Clone the repository:
```bash
git clone https://github.com/jefrnc/mt5-docker-api
cd mt5-docker-api
```

2. Build the image:
```bash
docker build -t mt5-docker-api:latest .
```

## System Requirements

- Docker Engine 20.10+
- 4GB RAM minimum
- 10GB disk space
- x86_64/amd64 architecture (ARM not supported)

## Security Considerations

- Always use strong passwords
- Run with minimal privileges
- Keep the image updated
- Use environment variables for sensitive data
- Consider network isolation for production use

## Troubleshooting

### Container won't start
- Check logs: `docker logs mt5`
- Verify ports 3000 and 8001 are not in use
- Ensure sufficient disk space

### Can't connect to VNC
- Verify container is running: `docker ps`
- Check firewall settings
- Try accessing `http://localhost:3000` directly

### MT5 installation fails
- Check internet connectivity
- Verify Wine is working: `docker exec mt5 wine --version`
- Review installation logs

### Python API connection issues
- Ensure port 8001 is exposed
- Check mt5linux server is running
- Verify network connectivity

## Performance Tips

- Allocate at least 2 CPU cores
- Use SSD storage for better I/O
- Limit concurrent connections
- Monitor resource usage

## License

This project is licensed under the MIT License. See [LICENSE.md](LICENSE.md) for details.