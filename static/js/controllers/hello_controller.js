import { application, Controller } from "../app.js"
import { StreamSubscriptionManager } from "../turbo-stream-source.js"

class HelloController extends Controller {
  static targets = ["name", "status"]

  connect() {
    // Set up status callback
    this.statusCallback = (text, className) => {
      if (this.hasStatusTarget) {
        this.statusTarget.textContent = text
        this.statusTarget.className = className
      }
    }

    StreamSubscriptionManager.addStatusCallback(this.statusCallback)

    // Note: The actual stream subscription is handled by <turbo-stream-source>
    // This controller just manages the UI and greet action
    StreamSubscriptionManager.connect()
  }

  disconnect() {
    // Remove status callback but keep WebSocket alive
    if (this.statusCallback) {
      StreamSubscriptionManager.removeStatusCallback(this.statusCallback)
    }
  }

  greet() {
    const name = this.nameTarget.value.trim()
    if (name) {
      // Send message to the greetings stream
      if (StreamSubscriptionManager.sendToStream("greetings", name)) {
        this.nameTarget.value = ""
        this.nameTarget.focus()
      }
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
