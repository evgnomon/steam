from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from typing import List
from datetime import datetime
import asyncio
import json


async def periodic_broadcaster():
    """Send a message to all clients every 5 seconds."""
    while True:
        await asyncio.sleep(5)
        if connected_clients:
            timestamp = datetime.now().strftime("%H:%M:%S")
            turbo_stream = f"""
<turbo-stream action="append" target="greetings">
  <template>
    <li style="color: #666; font-style: italic;">Server ping at {timestamp}</li>
  </template>
</turbo-stream>"""
            await broadcast(turbo_stream)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start periodic broadcaster on startup
    task = asyncio.create_task(periodic_broadcaster())
    yield
    # Cancel on shutdown
    task.cancel()


app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="templates")

# Store connected WebSocket clients
connected_clients: List[WebSocket] = []

# Simple in-memory storage for demo
greetings: List[str] = []

# Configuration
HEARTBEAT_INTERVAL = 30  # seconds
RECEIVE_TIMEOUT = 60  # seconds


async def broadcast(message: str, exclude: WebSocket = None):
    """Send message to all connected clients."""
    disconnected = []
    for client in connected_clients:
        if client == exclude:
            continue
        try:
            await client.send_text(message)
        except:
            disconnected.append(client)

    # Clean up disconnected clients
    for client in disconnected:
        if client in connected_clients:
            connected_clients.remove(client)


async def heartbeat(websocket: WebSocket):
    """Send periodic pings to keep connection alive."""
    try:
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            await websocket.send_text(json.dumps({"type": "ping"}))
    except:
        pass


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        "index.html", {"request": request, "greetings": greetings}
    )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)

    # Start heartbeat task
    heartbeat_task = asyncio.create_task(heartbeat(websocket))

    try:
        while True:
            # Wait for message with timeout
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(), timeout=RECEIVE_TIMEOUT
                )
            except asyncio.TimeoutError:
                # No message received in timeout period, check if still alive
                try:
                    await websocket.send_text(json.dumps({"type": "ping"}))
                    continue
                except:
                    break

            # Handle ping/pong
            try:
                msg = json.loads(data)
                if msg.get("type") in ("ping", "pong"):
                    # Respond to ping with pong
                    if msg.get("type") == "ping":
                        await websocket.send_text(json.dumps({"type": "pong"}))
                    continue
            except json.JSONDecodeError:
                pass  # Not JSON, treat as greeting message

            # Handle greeting message
            name = data.strip()
            if name:
                greeting = f"Hello, {name}!"
                greetings.append(greeting)

                # Broadcast Turbo Stream to ALL connected clients
                turbo_stream = f"""
<turbo-stream action="append" target="greetings">
  <template>
    <li>{greeting}</li>
  </template>
</turbo-stream>"""

                await broadcast(turbo_stream)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        # Clean up
        heartbeat_task.cancel()
        if websocket in connected_clients:
            connected_clients.remove(websocket)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
