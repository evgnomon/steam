import { Turbo } from "./app.js"

// Subscription manager - handles WebSocket subscriptions for Turbo Streams
const StreamSubscriptionManager = {
  socket: null,
  reconnectDelay: 1000,
  maxReconnectDelay: 30000,
  heartbeatInterval: 25000,
  heartbeat: null,
  reconnectTimeout: null,
  statusCallbacks: new Set(),

  // Track active subscriptions (stream name -> Set of elements)
  subscriptions: new Map(),
  // Pending subscriptions waiting for connection
  pendingSubscriptions: new Set(),

  getWsUrl() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:"
    const host = window.location.host
    return `${protocol}//${host}/ws`
  },

  connect() {
    // Already connected or connecting
    if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
      return
    }

    this.updateStatus("Connecting...", "status")

    this.socket = new WebSocket(this.getWsUrl())

    this.socket.onopen = () => {
      this.updateStatus("Connected", "status connected")
      this.reconnectDelay = 1000

      // Start heartbeat
      this.heartbeat = setInterval(() => {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
          this.socket.send(JSON.stringify({ type: "ping" }))
        }
      }, this.heartbeatInterval)

      // Re-subscribe to all active streams
      for (const streamName of this.subscriptions.keys()) {
        this.sendSubscribe(streamName)
      }

      // Process pending subscriptions
      for (const streamName of this.pendingSubscriptions) {
        this.sendSubscribe(streamName)
      }
      this.pendingSubscriptions.clear()
    }

    this.socket.onclose = () => {
      this.updateStatus(`Disconnected - Reconnecting in ${this.reconnectDelay / 1000}s...`, "status disconnected")

      if (this.heartbeat) {
        clearInterval(this.heartbeat)
        this.heartbeat = null
      }

      this.reconnectTimeout = setTimeout(() => {
        this.socket = null
        this.connect()
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
        if (msg.type === "subscribed") {
          console.log(`Subscribed to stream: ${msg.stream}`)
          return
        }
        if (msg.type === "unsubscribed") {
          console.log(`Unsubscribed from stream: ${msg.stream}`)
          return
        }
      } catch (e) {
        // Not JSON, must be Turbo Stream
      }

      // Render Turbo Stream message
      Turbo.renderStreamMessage(event.data)
    }
  },

  sendSubscribe(streamName) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({ type: "subscribe", stream: streamName }))
    }
  },

  sendUnsubscribe(streamName) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({ type: "unsubscribe", stream: streamName }))
    }
  },

  subscribe(streamName, element) {
    // Track element subscription
    if (!this.subscriptions.has(streamName)) {
      this.subscriptions.set(streamName, new Set())
    }
    this.subscriptions.get(streamName).add(element)

    // Ensure WebSocket connection exists
    this.connect()

    // If connected, subscribe immediately; otherwise queue it
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      // Only send subscribe if this is the first element for this stream
      if (this.subscriptions.get(streamName).size === 1) {
        this.sendSubscribe(streamName)
      }
    } else {
      this.pendingSubscriptions.add(streamName)
    }
  },

  unsubscribe(streamName, element) {
    if (!this.subscriptions.has(streamName)) {
      return
    }

    this.subscriptions.get(streamName).delete(element)

    // If no more elements subscribed to this stream, unsubscribe from server
    if (this.subscriptions.get(streamName).size === 0) {
      this.subscriptions.delete(streamName)
      this.sendUnsubscribe(streamName)
    }
  },

  updateStatus(text, className) {
    for (const callback of this.statusCallbacks) {
      callback(text, className)
    }
  },

  addStatusCallback(callback) {
    this.statusCallbacks.add(callback)
    // Immediately update with current status
    if (this.socket) {
      if (this.socket.readyState === WebSocket.OPEN) {
        callback("Connected", "status connected")
      } else if (this.socket.readyState === WebSocket.CONNECTING) {
        callback("Connecting...", "status")
      }
    }
  },

  removeStatusCallback(callback) {
    this.statusCallbacks.delete(callback)
  },

  send(data) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(data)
      return true
    }
    return false
  },

  sendToStream(streamName, content) {
    return this.send(JSON.stringify({
      type: "message",
      stream: streamName,
      content: content
    }))
  }
}

// Initialize visibility change handler once globally
if (!window._streamVisibilityHandlerSet) {
  window._streamVisibilityHandlerSet = true
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") {
      if (!StreamSubscriptionManager.socket || StreamSubscriptionManager.socket.readyState !== WebSocket.OPEN) {
        StreamSubscriptionManager.connect()
      }
    }
  })
}

// Custom element: <turbo-stream-source stream="stream-name">
// Automatically subscribes when connected to DOM, unsubscribes when disconnected
class TurboStreamSourceElement extends HTMLElement {
  static get observedAttributes() {
    return ["stream"]
  }

  get stream() {
    return this.getAttribute("stream")
  }

  set stream(value) {
    if (value) {
      this.setAttribute("stream", value)
    } else {
      this.removeAttribute("stream")
    }
  }

  connectedCallback() {
    const streamName = this.stream
    if (streamName) {
      console.log(`<turbo-stream-source> connected: subscribing to "${streamName}"`)
      StreamSubscriptionManager.subscribe(streamName, this)
    }
  }

  disconnectedCallback() {
    const streamName = this.stream
    if (streamName) {
      console.log(`<turbo-stream-source> disconnected: unsubscribing from "${streamName}"`)
      StreamSubscriptionManager.unsubscribe(streamName, this)
    }
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (name === "stream" && this.isConnected) {
      // Stream changed while connected - unsubscribe from old, subscribe to new
      if (oldValue) {
        StreamSubscriptionManager.unsubscribe(oldValue, this)
      }
      if (newValue) {
        StreamSubscriptionManager.subscribe(newValue, this)
      }
    }
  }
}

// Register the custom element
if (!customElements.get("turbo-subscribe")) {
  customElements.define("turbo-subscribe", TurboStreamSourceElement)
}

export { StreamSubscriptionManager, TurboStreamSourceElement }
