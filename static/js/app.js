import {
  Application,
  Controller,
} from "https://unpkg.com/@hotwired/stimulus/dist/stimulus.js";
import * as Turbo from "https://unpkg.com/@hotwired/turbo@8/dist/turbo.es2017-esm.js";

// Only initialize once to prevent duplicate WebSocket connections
if (!window.Turbo) {
  window.Turbo = Turbo;
}

if (!window.application) {
  window.Application = Application;
  window.Controller = Controller;
  window.application = Application.start();
  console.log("Stimulus and Turbo have been initialized.", window.application);
}

const application = window.application;

console.log("App module loaded.", application);

export { Application, Controller, Turbo, application };
