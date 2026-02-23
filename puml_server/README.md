# PlantUML Local Generator (FastAPI)

Quick scaffold for a local FastAPI server that accepts PlantUML and returns generated artifacts.

Usage:

1. Create a virtualenv and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Run server:

```powershell
cd puml_server
python server.py
```

3. Token / Pairing flow:

- On first run a token is written to `puml_server/token.txt`. You can copy it and paste into the extension's Token field.
- Recommended pairing flow (safer):
	1. On the machine running the server, request a one-time pairing code (local-only):

```powershell
curl http://127.0.0.1:8000/pair-code
```

	2. The server returns a short code (valid a few minutes). In the extension popup enter the code or use the popup to call `POST /pair` with the code — the extension will receive the token and store it.

	3. The extension will use the token in `Authorization: Bearer <token>` for subsequent requests.

This flow reduces exposing the long-lived token directly and ensures only allowed origins (e.g., https://editor.plantuml.com) can complete pairing.

Endpoints:
- `POST /generate` — submit PlantUML JSON payload
- `GET /status/{job_id}` — check status
- `GET /files/{job_id}.zip` — download artifacts

This is a minimal scaffold. Replace `make_artifacts` with real generator integration.
