from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from typing import List, Optional
from datetime import datetime
import asyncio
import json
import random


async def periodic_broadcaster():
    """Send a message to all clients every 5 seconds."""
    while True:
        await asyncio.sleep(5)
        if connected_clients:
            timestamp = datetime.now().strftime("%H:%M:%S")
            message = f"Server ping at {timestamp}"
            greetings.append(message)
            turbo_stream = f"""
<turbo-stream action="append" target="greetings">
  <template>
    <li style="color: #666; font-style: italic;">{message}</li>
  </template>
</turbo-stream>"""
            await broadcast(turbo_stream)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Start periodic broadcaster on startup
    task = asyncio.create_task(periodic_broadcaster())
    yield
    # Cancel on shutdown
    task.cancel()


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Store connected WebSocket clients
connected_clients: List[WebSocket] = []

# Simple in-memory storage for demo
greetings: List[str] = []

# Configuration
HEARTBEAT_INTERVAL = 30  # seconds
RECEIVE_TIMEOUT = 60  # seconds


async def broadcast(message: str, exclude: Optional[WebSocket] = None):
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


@app.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})


@app.get("/frames", response_class=HTMLResponse)
async def frames(request: Request):
    return templates.TemplateResponse("frames.html", {"request": request})


QUOTES = [
    "The best way to predict the future is to invent it.",
    "Simplicity is the ultimate sophistication.",
    "First, solve the problem. Then, write the code.",
    "Code is like humor. When you have to explain it, it's bad.",
    "Any fool can write code that a computer can understand. Good programmers write code that humans can understand.",
]

@app.get("/frames/quote", response_class=HTMLResponse)
async def frames_quote(request: Request):
    quote = random.choice(QUOTES)
    return templates.TemplateResponse("frames/quote.html", {"request": request, "quote": quote})


TAB_CONTENT = {
    1: "This is the content for the first tab. Notice the URL didn't change and the rest of the page stayed intact.",
    2: "Here's the second tab content. Turbo Frames only replace the matching frame element.",
    3: "Third tab loaded! Each frame request is a real HTTP request, but only the frame updates.",
}

@app.get("/frames/tab/{tab_id}", response_class=HTMLResponse)
async def frames_tab(request: Request, tab_id: int):
    content = TAB_CONTENT.get(tab_id, "Tab not found")
    timestamp = datetime.now().strftime("%H:%M:%S")
    return templates.TemplateResponse("frames/tab.html", {
        "request": request,
        "tab_id": tab_id,
        "content": content,
        "timestamp": timestamp,
    })


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
