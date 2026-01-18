import { application, Controller } from "../app.js"
import { StreamSubscriptionManager } from "../turbo-stream-source.js"

class StreamsDemoController extends Controller {
  static targets = ["status", "name", "notificationsContainer", "alertsContainer", "notificationsBtn", "alertsBtn"]

  connect() {
    this.statusCallback = (text, className) => {
      if (this.hasStatusTarget) {
        this.statusTarget.textContent = text
        this.statusTarget.className = className
      }
    }

    StreamSubscriptionManager.addStatusCallback(this.statusCallback)
    StreamSubscriptionManager.connect()

    // Track subscription state
    this.notificationsSubscribed = false
    this.alertsSubscribed = false
  }

  disconnect() {
    if (this.statusCallback) {
      StreamSubscriptionManager.removeStatusCallback(this.statusCallback)
    }
  }

  toggleNotifications() {
    const container = this.notificationsContainerTarget
    const btn = this.notificationsBtnTarget

    if (this.notificationsSubscribed) {
      // Remove the stream source element - this triggers unsubscribe
      container.innerHTML = '<p><em>Not subscribed to notifications stream</em></p><ul id="notifications"></ul>'
      btn.textContent = "Subscribe to Notifications"
      this.notificationsSubscribed = false
    } else {
      // Add the stream source element - this triggers subscribe
      container.innerHTML = '<turbo-stream-source stream="notifications"></turbo-stream-source><p><em>Subscribed! Messages will appear below.</em></p><ul id="notifications"></ul>'
      btn.textContent = "Unsubscribe from Notifications"
      this.notificationsSubscribed = true
    }
  }

  toggleAlerts() {
    const container = this.alertsContainerTarget
    const btn = this.alertsBtnTarget

    if (this.alertsSubscribed) {
      // Remove the stream source element - this triggers unsubscribe
      container.innerHTML = '<p><em>Not subscribed to alerts stream</em></p><ul id="alerts"></ul>'
      btn.textContent = "Subscribe to Alerts"
      this.alertsSubscribed = false
    } else {
      // Add the stream source element - this triggers subscribe
      container.innerHTML = '<turbo-stream-source stream="alerts"></turbo-stream-source><p><em>Subscribed! Alerts will appear below.</em></p><ul id="alerts"></ul>'
      btn.textContent = "Unsubscribe from Alerts"
      this.alertsSubscribed = true
    }
  }

  greet() {
    const name = this.nameTarget.value.trim()
    if (name) {
      if (StreamSubscriptionManager.sendToStream("greetings", name)) {
        this.nameTarget.value = ""
        this.nameTarget.focus()
      }
    }
  }

  sendNotification() {
    const timestamp = new Date().toLocaleTimeString()
    StreamSubscriptionManager.sendToStream("notifications", `Notification at ${timestamp}`)
  }

  sendAlert() {
    const timestamp = new Date().toLocaleTimeString()
    StreamSubscriptionManager.sendToStream("alerts", `Alert at ${timestamp}`)
  }
}

// Only register if not already registered
if (!window._registeredControllers?.has("streams-demo")) {
  window._registeredControllers = window._registeredControllers || new Set()
  window._registeredControllers.add("streams-demo")
  application.register("streams-demo", StreamsDemoController)
}

export { StreamsDemoController }
