# Stimulus + Turbo + WebSocket + FastAPI

Minimal Hotwire setup with WebSocket for real-time updates. No JS build tools.

## Project Structure

```
stimulus-hello/
├── app.py              # FastAPI with WebSocket endpoint
├── requirements.txt    # Python dependencies
├── templates/
│   └── index.html      # Jinja2 template with Turbo + Stimulus
└── README.md
```

## Setup

```bash
# Create virtual environment (optional)
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Run the server
python app.py
```

Then open http://localhost:8000

## How It Works

1. **Stimulus controller** manages WebSocket connection
2. User types name and clicks Greet (or presses Enter)
3. Message sent to server via **WebSocket**
4. Server **broadcasts Turbo Stream** to ALL connected clients
5. **Turbo** renders the stream, appending new greeting to the list

## Connection Stability Features

### Client Side
- **Heartbeat ping** every 25 seconds to keep connection alive
- **Exponential backoff** reconnection (1s → 2s → 4s → ... → 30s max)
- **Visibility API** - auto-reconnect when tab becomes active
- **Proper cleanup** on disconnect

### Server Side
- **Heartbeat ping** every 30 seconds
- **Receive timeout** (60s) to detect dead clients
- **Ping/pong handling** - responds to client pings
- **Graceful cleanup** of disconnected clients

## Real-time Features

- Open multiple browser tabs to see real-time sync
- All connected clients see new greetings instantly
- Auto-reconnect on disconnect with backoff
- Connection status indicator

## Key Files

- `app.py`: WebSocket endpoint with heartbeat and timeout handling
- `templates/index.html`: Stimulus controller with robust connection management
