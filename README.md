# HTTP Request Runner Panel

Web-based HTTP POST / Request Runner panel built with FastAPI.

## Features
- Real-time HTTP request runner with configurable interval (down to 0.01s).
- Dynamic payload configuration with instant 2 MB test payload loader.
- Live stats dashboard (total sent, success, fails, latency, bandwidth, last status).
- Automatic PORT detection for cloud deployment platforms (Render, Railway, Fly.io, etc.).

## Run Locally

```bash
pip install -r requirements.txt
python main.py
```

Open `http://localhost:8083` in your browser.

## Run with Docker

```bash
docker build -t postrnumber .
docker run -p 8083:8083 postrnumber
```
