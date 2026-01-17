import { Application, Controller } from "https://unpkg.com/@hotwired/stimulus/dist/stimulus.js"

// Start Stimulus application
const application = Application.start()

class HelloController extends Controller {
  static targets = ["name", "output"]

  greet() {
    const name = this.nameTarget.value.trim()
    this.outputTarget.textContent = name ? `Hello, ${name}!` : "Hello!"
  }
}

// Register the controller
application.register("hello", HelloController)

export { HelloController }
