import { application, Controller, Turbo } from "../app.js"

// Global WebSocket manager to persist connection across Turbo navigations
const WebSocketManager = {
  socket: null,
  reconnectDelay: 1000,
  maxReconnectDelay: 30000,
  heartbeatInterval: 25000,
  heartbeat: null,
  reconnectTimeout: null,
  statusCallback: null,

  getWsUrl() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:"
    const host = window.location.host
    return `${protocol}//${host}/ws`
  },

  connect(statusCallback) {
    this.statusCallback = statusCallback

    // Already connected or connecting
    if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
      this.updateStatus("Connected", "status connected")
      return
    }

    this.updateStatus("Connecting...", "status")

    this.socket = new WebSocket(this.getWsUrl())

    this.socket.onopen = () => {
      this.updateStatus("Connected", "status connected")
      this.reconnectDelay = 1000

      this.heartbeat = setInterval(() => {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
          this.socket.send(JSON.stringify({ type: "ping" }))
        }
      }, this.heartbeatInterval)
    }

    this.socket.onclose = () => {
      this.updateStatus(`Disconnected - Reconnecting in ${this.reconnectDelay / 1000}s...`, "status disconnected")

      if (this.heartbeat) {
        clearInterval(this.heartbeat)
        this.heartbeat = null
      }

      this.reconnectTimeout = setTimeout(() => {
        this.socket = null
        this.connect(this.statusCallback)
      }, this.reconnectDelay)

      this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay)
    }

    this.socket.onerror = (error) => {
      console.error("WebSocket error:", error)
      this.updateStatus("Connection error", "status disconnected")
    }

    this.socket.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        if (msg.type === "ping") {
          this.socket.send(JSON.stringify({ type: "pong" }))
          return
        }
        if (msg.type === "pong") {
          return
        }
      } catch (e) {
        // Not JSON, must be Turbo Stream
      }

      Turbo.renderStreamMessage(event.data)
    }
  },

  updateStatus(text, className) {
    if (this.statusCallback) {
      this.statusCallback(text, className)
    }
  },

  setStatusCallback(callback) {
    this.statusCallback = callback
    // Immediately update with current status
    if (this.socket) {
      if (this.socket.readyState === WebSocket.OPEN) {
        this.updateStatus("Connected", "status connected")
      } else if (this.socket.readyState === WebSocket.CONNECTING) {
        this.updateStatus("Connecting...", "status")
      }
    }
  },

  send(data) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(data)
      return true
    }
    return false
  }
}

// Initialize visibility change handler once globally
if (!window._wsVisibilityHandlerSet) {
  window._wsVisibilityHandlerSet = true
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") {
      if (!WebSocketManager.socket || WebSocketManager.socket.readyState !== WebSocket.OPEN) {
        WebSocketManager.connect(WebSocketManager.statusCallback)
      }
    }
  })
}

class HelloController extends Controller {
  static targets = ["name", "status"]

  connect() {
    // Set up status callback and connect (or reuse existing connection)
    WebSocketManager.setStatusCallback((text, className) => {
      if (this.hasStatusTarget) {
        this.statusTarget.textContent = text
        this.statusTarget.className = className
      }
    })

    WebSocketManager.connect((text, className) => {
      if (this.hasStatusTarget) {
        this.statusTarget.textContent = text
        this.statusTarget.className = className
      }
    })
  }

  disconnect() {
    // Don't close WebSocket on Turbo navigation - keep it alive
    WebSocketManager.setStatusCallback(null)
  }

  greet() {
    const name = this.nameTarget.value.trim()
    if (name && WebSocketManager.send(name)) {
      this.nameTarget.value = ""
      this.nameTarget.focus()
    }
  }
}

// Only register if not already registered
if (!window._registeredControllers?.has("hello")) {
  window._registeredControllers = window._registeredControllers || new Set()
  window._registeredControllers.add("hello")
  application.register("hello", HelloController)
}

export { HelloController }
