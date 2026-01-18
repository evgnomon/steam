from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from typing import Dict, List, Set, Optional
from datetime import datetime
import asyncio
import json
import random


# Stream subscription management
# Maps stream names to sets of subscribed WebSocket connections
stream_subscriptions: Dict[str, Set[WebSocket]] = {}
# Maps WebSocket connections to their subscribed streams (for cleanup)
client_streams: Dict[WebSocket, Set[str]] = {}


def subscribe_to_stream(websocket: WebSocket, stream_name: str) -> bool:
    """Subscribe a client to a stream. Returns True if newly subscribed."""
    if stream_name not in stream_subscriptions:
        stream_subscriptions[stream_name] = set()

    if websocket in stream_subscriptions[stream_name]:
        return False  # Already subscribed

    stream_subscriptions[stream_name].add(websocket)

    if websocket not in client_streams:
        client_streams[websocket] = set()
    client_streams[websocket].add(stream_name)

    print(f"Client subscribed to stream: {stream_name} (total: {len(stream_subscriptions[stream_name])})")
    return True


def unsubscribe_from_stream(websocket: WebSocket, stream_name: str) -> bool:
    """Unsubscribe a client from a stream. Returns True if was subscribed."""
    if stream_name not in stream_subscriptions:
        return False

    if websocket not in stream_subscriptions[stream_name]:
        return False

    stream_subscriptions[stream_name].discard(websocket)

    if websocket in client_streams:
        client_streams[websocket].discard(stream_name)

    # Clean up empty stream sets
    if not stream_subscriptions[stream_name]:
        del stream_subscriptions[stream_name]

    print(f"Client unsubscribed from stream: {stream_name}")
    return True


def cleanup_client_subscriptions(websocket: WebSocket):
    """Remove all subscriptions for a disconnected client."""
    if websocket not in client_streams:
        return

    streams = list(client_streams[websocket])
    for stream_name in streams:
        unsubscribe_from_stream(websocket, stream_name)

    if websocket in client_streams:
        del client_streams[websocket]


async def broadcast_to_stream(stream_name: str, message: str, exclude: Optional[WebSocket] = None):
    """Send message only to clients subscribed to a specific stream."""
    if stream_name not in stream_subscriptions:
        return

    disconnected = []
    for client in stream_subscriptions[stream_name]:
        if client == exclude:
            continue
        try:
            await client.send_text(message)
        except:
            disconnected.append(client)

    # Clean up disconnected clients
    for client in disconnected:
        cleanup_client_subscriptions(client)


async def periodic_broadcaster():
    """Send a message to greetings stream subscribers every 5 seconds."""
    while True:
        await asyncio.sleep(5)
        if "greetings" in stream_subscriptions and stream_subscriptions["greetings"]:
            timestamp = datetime.now().strftime("%H:%M:%S")
            message = f"Server ping at {timestamp}"
            greetings.append(message)
            turbo_stream = f"""
<turbo-stream action="append" target="greetings">
  <template>
    <li style="color: #666; font-style: italic;">{message}</li>
  </template>
</turbo-stream>"""
            await broadcast_to_stream("greetings", turbo_stream)


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

# Simple in-memory storage for demo
greetings: List[str] = []

# Configuration
HEARTBEAT_INTERVAL = 30  # seconds
RECEIVE_TIMEOUT = 60  # seconds


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


@app.get("/streams", response_class=HTMLResponse)
async def streams(request: Request):
    return templates.TemplateResponse(
        "streams.html", {"request": request, "greetings": greetings}
    )


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

            # Handle JSON messages (ping/pong, subscribe, unsubscribe)
            try:
                msg = json.loads(data)
                msg_type = msg.get("type")

                if msg_type == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                    continue
                elif msg_type == "pong":
                    continue
                elif msg_type == "subscribe":
                    stream_name = msg.get("stream")
                    if stream_name:
                        subscribed = subscribe_to_stream(websocket, stream_name)
                        await websocket.send_text(json.dumps({
                            "type": "subscribed",
                            "stream": stream_name,
                            "success": subscribed
                        }))
                    continue
                elif msg_type == "unsubscribe":
                    stream_name = msg.get("stream")
                    if stream_name:
                        unsubscribed = unsubscribe_from_stream(websocket, stream_name)
                        await websocket.send_text(json.dumps({
                            "type": "unsubscribed",
                            "stream": stream_name,
                            "success": unsubscribed
                        }))
                    continue
                elif msg_type == "message":
                    # Handle messages sent to a specific stream
                    stream_name = msg.get("stream")
                    content = msg.get("content", "").strip()
                    if stream_name and content:
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        if stream_name == "greetings":
                            greeting = f"Hello, {content}!"
                            greetings.append(greeting)
                            turbo_stream = f"""
<turbo-stream action="append" target="greetings">
  <template>
    <li>{greeting}</li>
  </template>
</turbo-stream>"""
                            await broadcast_to_stream("greetings", turbo_stream)
                        elif stream_name == "notifications":
                            turbo_stream = f"""
<turbo-stream action="append" target="notifications">
  <template>
    <li><strong>{timestamp}</strong>: {content}</li>
  </template>
</turbo-stream>"""
                            await broadcast_to_stream("notifications", turbo_stream)
                        elif stream_name == "alerts":
                            turbo_stream = f"""
<turbo-stream action="append" target="alerts">
  <template>
    <li style="color: #dc3545;"><strong>{timestamp}</strong>: {content}</li>
  </template>
</turbo-stream>"""
                            await broadcast_to_stream("alerts", turbo_stream)
                    continue
            except json.JSONDecodeError:
                pass  # Not JSON, treat as legacy greeting message

            # Handle legacy greeting message (plain text)
            name = data.strip()
            if name:
                greeting = f"Hello, {name}!"
                greetings.append(greeting)

                # Broadcast to greetings stream subscribers
                turbo_stream = f"""
<turbo-stream action="append" target="greetings">
  <template>
    <li>{greeting}</li>
  </template>
</turbo-stream>"""

                await broadcast_to_stream("greetings", turbo_stream)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        # Clean up all subscriptions for this client
        heartbeat_task.cancel()
        cleanup_client_subscriptions(websocket)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
