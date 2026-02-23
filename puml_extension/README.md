# PlantUML Connector Extension

Scaffold Chrome extension to send PlantUML from https://editor.plantuml.com/ to your local generator server.

Install (developer mode):

1. Open `chrome://extensions`
2. Enable "Developer mode"
3. Click "Load unpacked" and select the `puml_extension` folder in this repo

Usage:
- Open https://editor.plantuml.com/
- Click the extension icon, set `Server URL` (e.g. `http://localhost:8000`) and `Token` (from server/token.txt), choose method and `Save`.
- Click `Send current PUML` or use the floating "Send to Local Generator" button injected into the page.

Notes:
- The content script attempts to read common editor textareas; if it cannot detect code you'll be prompted to paste it.
- This is a minimal scaffold; improve selectors and UX as needed.
