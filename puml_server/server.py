import os
import uuid
import json
import base64
import shutil
import zipfile
from pathlib import Path
import re

# import generator API
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from main import detect_generator_from_data
from datetime import datetime
from typing import Optional, Dict, Any, List
import subprocess
import importlib
import traceback

from fastapi import FastAPI, HTTPException, Header, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = BASE_DIR / "storage"
STORAGE_DIR.mkdir(exist_ok=True)
TOKEN_FILE = BASE_DIR / "token.txt"


def persist_parsed_result(result: dict, puml: str):
    """Persist parsed JSON and input PUML to a new job folder and return job_id and parsed_file path."""
    try:
        job_id = uuid.uuid4().hex
        job_dir = STORAGE_DIR / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        parsed_file = job_dir / "parsed.json"
        parsed_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        (job_dir / "input.puml").write_text(puml, encoding="utf-8")
        print(f"Saved parsed JSON to {parsed_file}")
        return job_id, parsed_file
    except Exception as e:
        print("Failed to persist parsed JSON:", e)
        return None, None


def run_plugin_runner(parsed_json_path: Path, diagram_type: Optional[str], languages: Optional[list]):
    """Invoke plugin_runner.py as a subprocess and return its stdout/stderr and saved path if found."""
    if not diagram_type:
        return {"status": "skipped", "reason": "no diagram_type provided"}

    # Try in-process generation using detect_generator_from_data to ensure files are written
    try:
        data = json.loads(parsed_json_path.read_text(encoding='utf-8'))
    except Exception as e:
        return {"status": "error", "reason": f"failed to read parsed json: {e}"}

    # Validate there's meaningful content for requested diagram type
    has_content = False
    if diagram_type == 'classes' and data.get('classes'):
        has_content = True
    if diagram_type == 'database' and data.get('tables'):
        has_content = True
    if diagram_type == 'deployment' and data.get('nodes'):
        has_content = True

    if not has_content:
        return {"status": "skipped", "reason": "parsed JSON does not contain required keys for diagram type", "parsed_keys": list(data.keys())}

    outputs = []
    plugin_out_dir = parsed_json_path.parent / 'plugin_outputs'
    plugin_out_dir.mkdir(parents=True, exist_ok=True)

    # languages may be comma-separated string or list
    if isinstance(languages, str):
        languages = [x.strip() for x in languages.split(',') if x.strip()]

    # decide job-level id
    run_id = uuid.uuid4().hex
    run_dir = plugin_out_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    try:
        # For classes: run per language
        if diagram_type == 'classes':
            langs = languages or ['python']
            for lang in langs:
                try:
                    gen = detect_generator_from_data(data, prefer_language=lang, validate_code=False)
                    gen.file_path = parsed_json_path
                    out_name = Path(gen.output_file).name if hasattr(gen, 'output_file') else f'output_{lang}.txt'
                    gen.output_file = run_dir / out_name
                    gen.generate()
                    # if generator wrote file, copy/check it
                    if gen.output_file and Path(gen.output_file).exists():
                        outputs.append(str(gen.output_file))
                    else:
                        # try to find files in common generated dirs
                        copied = []
                        for d in [Path('generated_code'), Path('generated_sql')]:
                            if d.exists():
                                for f in d.rglob('*'):
                                    if f.is_file():
                                        dest = run_dir / f.name
                                        try:
                                            shutil.copyfile(f, dest)
                                            copied.append(str(dest))
                                        except Exception:
                                            pass
                        if copied:
                            outputs.extend(copied)
                        else:
                            outputs.append({'language': lang, 'warning': 'no output file produced'})
                except Exception as e:
                    err_path = run_dir / f'error_{lang}.txt'
                    try:
                        err_path.write_text(traceback.format_exc(), encoding='utf-8')
                    except Exception:
                        pass
                    outputs.append({'language': lang, 'error': str(e), 'trace': str(err_path)})

        # For database: run per DB type
        elif diagram_type == 'database':
            dbs = languages or ['postgresql']
            for db in dbs:
                try:
                    gen = detect_generator_from_data(data, prefer_language=None, validate_code=False, db_type=db)
                    gen.file_path = parsed_json_path
                    out_name = Path(gen.output_file).name if hasattr(gen, 'output_file') else f'output_{db}.sql'
                    gen.output_file = run_dir / out_name
                    gen.generate()
                    if gen.output_file and Path(gen.output_file).exists():
                        outputs.append(str(gen.output_file))
                    else:
                        # scan generated_sql
                        copied = []
                        d = Path('generated_sql')
                        if d.exists():
                            for f in d.rglob('*'):
                                if f.is_file():
                                    dest = run_dir / f.name
                                    try:
                                        shutil.copyfile(f, dest)
                                        copied.append(str(dest))
                                    except Exception:
                                        pass
                        if copied:
                            outputs.extend(copied)
                        else:
                            outputs.append({'db': db, 'warning': 'no output file produced'})
                except Exception as e:
                    err_path = run_dir / f'error_{db}.txt'
                    try:
                        err_path.write_text(traceback.format_exc(), encoding='utf-8')
                    except Exception:
                        pass
                    outputs.append({'db': db, 'error': str(e), 'trace': str(err_path)})

        # For deployment: single generator
        elif diagram_type == 'deployment':
            try:
                gen = detect_generator_from_data(data, prefer_language=None, validate_code=False)
                gen.file_path = parsed_json_path
                out_name = Path(gen.output_file).name if hasattr(gen, 'output_file') else 'docker-compose.yaml'
                gen.output_file = run_dir / out_name
                gen.generate()
                if gen.output_file and Path(gen.output_file).exists():
                    outputs.append(str(gen.output_file))
                else:
                    # try to find written file in generated_code
                    copied = []
                    d = Path('generated_code')
                    if d.exists():
                        for f in d.rglob('*'):
                            if f.is_file():
                                dest = run_dir / f.name
                                try:
                                    shutil.copyfile(f, dest)
                                    copied.append(str(dest))
                                except Exception:
                                    pass
                    if copied:
                        outputs.extend(copied)
                    else:
                        outputs.append({'warning': 'no output file produced'})
            except Exception as e:
                err_path = run_dir / 'error_deployment.txt'
                try:
                    err_path.write_text(traceback.format_exc(), encoding='utf-8')
                except Exception:
                    pass
                outputs.append({'error': str(e), 'trace': str(err_path)})

        return {"status": "ok", "run_dir": str(run_dir), "outputs": outputs}
    except Exception as e:
        return {"status": "error", "reason": str(e), "trace": traceback.format_exc()}


def infer_diagram_type_from_keys(parsed_keys: Optional[list]) -> str:
    keys = set(parsed_keys or [])
    if "classes" in keys:
        return "classes"
    if "tables" in keys:
        return "database"
    if "nodes" in keys:
        return "deployment"
    return "unknown"


def run_plugin_runner_checked(parsed_json_path: Path, diagram_type: Optional[str], languages: Optional[list]):
    """Run generator and convert mismatch/failure into explicit HTTP errors."""
    plugin_result = run_plugin_runner(parsed_json_path, diagram_type, languages)
    if not isinstance(plugin_result, dict):
        return plugin_result

    status = plugin_result.get("status")
    if status == "skipped":
        reason = plugin_result.get("reason", "")
        if "required keys for diagram type" in reason:
            parsed_keys = plugin_result.get("parsed_keys", [])
            detected_type = infer_diagram_type_from_keys(parsed_keys)
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Selected diagram type '{diagram_type}' does not match parsed diagram type "
                    f"'{detected_type}'. Parsed keys: {parsed_keys}"
                ),
            )
    elif status == "error":
        raise HTTPException(status_code=500, detail=f"Generation failed: {plugin_result.get('reason', 'unknown error')}")

    return plugin_result


def collect_generated_files(job_id: str) -> List[Path]:
    """Collect generated artifacts for a job.

    Prefer files from the latest plugin run directory. If that is unavailable,
    fallback to files written directly into the job directory.
    """
    job_dir = STORAGE_DIR / job_id
    if not job_dir.exists():
        return []

    plugin_root = job_dir / "plugin_outputs"
    if plugin_root.exists():
        run_dirs = [d for d in plugin_root.iterdir() if d.is_dir()]
        if run_dirs:
            run_dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            latest_run_dir = run_dirs[0]
            files = [f for f in latest_run_dir.rglob("*") if f.is_file() and not f.name.startswith("error_")]
            if files:
                return files

    ignored = {"input.puml", "parsed.json", "README.md", "input.json"}
    return [f for f in job_dir.rglob("*") if f.is_file() and f.name not in ignored]


def ensure_token() -> str:
    if TOKEN_FILE.exists():
        return TOKEN_FILE.read_text().strip()
    t = uuid.uuid4().hex
    TOKEN_FILE.write_text(t)
    return t


SERVER_TOKEN = ensure_token()

app = FastAPI(title="PlantUML Local Generator")

# Configure allowed origins. Default to editor.plantuml.com for safety.
_origins = os.getenv("PUML_ALLOW_ORIGINS")
if _origins:
    ALLOW_ORIGINS = [o.strip() for o in _origins.split(",") if o.strip()]
else:
    ALLOW_ORIGINS = ["https://editor.plantuml.com"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)


class GenerateRequest(BaseModel):
    puml: str
    method: str
    options: Optional[Dict[str, Any]] = None
    sync: Optional[bool] = False
    callback_url: Optional[str] = None
    request_id: Optional[str] = None


# Pairing codes for one-time pairing flow: code -> expiry_ts
PAIR_CODES: Dict[str, float] = {}
PAIR_CODE_TTL = int(os.getenv("PUML_PAIR_TTL", "300"))  # seconds


def generate_pair_code() -> str:
    code = str(uuid.uuid4().hex[:6]).upper()
    PAIR_CODES[code] = datetime.utcnow().timestamp() + PAIR_CODE_TTL
    print(f"Pair code generated: {code} (valid {PAIR_CODE_TTL}s)")
    return code


def cleanup_pair_codes():
    now = datetime.utcnow().timestamp()
    expired = [c for c, ts in PAIR_CODES.items() if ts < now]
    for c in expired:
        del PAIR_CODES[c]



# Simple in-memory job store (replace with DB for production)
JOBS: Dict[str, Dict[str, Any]] = {}


def check_auth(authorization: Optional[str]):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header")
    token = authorization.split(None, 1)[1]
    if token != SERVER_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid token")


def parse_plantuml_classes(puml_text: str) -> dict:
    """Very small PlantUML class parser -> JSON structure expected by generators.

    Supports basic blocks like:
      class A {
        +attr: int
        +method(x: int): void
      }
    """
    classes = []
    # find class blocks
    for m in re.finditer(r"class\s+(\w+)\s*\{([^}]*)\}", puml_text, re.S):
        name = m.group(1)
        body = m.group(2)
        attrs = []
        methods = []
        for line in body.splitlines():
            line = line.strip()
            if not line:
                try:
                    job_id = uuid.uuid4().hex
                    job_dir = STORAGE_DIR / job_id
                    job_dir.mkdir(parents=True, exist_ok=True)
                    parsed_file = job_dir / "parsed.json"
                    parsed_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
                    (job_dir / "input.puml").write_text(puml, encoding="utf-8")
                    print(f"Saved parsed JSON to {parsed_file}")
                except Exception as _e:
                    print("Failed to persist parsed JSON:", _e)
                diagram_type = None
                languages = None
                try:
                    diagram_type = payload.get('diagramType') or payload.get('diagram_type')
                    languages = payload.get('languages') or payload.get('langs')
                except Exception:
                    pass
                plugin_result = None
                if diagram_type:
                    plugin_result = run_plugin_runner_checked(parsed_file, diagram_type, languages)
                    print("plugin_runner result:", plugin_result)
                return {"status": "ok", "result": result, "job_id": job_id, "plugin": plugin_result}
            # fallback: ignore
        classes.append({"name": name, "attributes": attrs, "methods": methods})
    return {"classes": classes}


def make_artifacts(job_id: str, puml: str, method: str, options: Optional[dict]) -> Path:
    """Generate artifacts by integrating with existing generator in main.py.

    If `puml` contains PlantUML class blocks, attempt to parse to JSON and run appropriate generator.
    Otherwise, create a simple text artifact fallback.
    """
    job_dir = STORAGE_DIR / job_id
    if job_dir.exists():
        shutil.rmtree(job_dir)
    job_dir.mkdir(parents=True)

    # If looks like PlantUML, parse classes
    if "@startuml" in puml or "class" in puml:
        data = parse_plantuml_classes(puml)
        # allow overriding language via options
        prefer_lang = None
        if options and isinstance(options, dict):
            prefer_lang = options.get("language") or options.get("lang")
        # Build a temp json file for generator
        tmp_json = job_dir / "input.json"
        tmp_json.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        # detect generator non-interactively
        gen = detect_generator_from_data(data, prefer_language=(prefer_lang or method), validate_code=bool(options and options.get("validate")))

        # override generator file paths to write into job_dir
        gen.file_path = tmp_json
        # choose sensible output filenames based on language
        if hasattr(gen, 'output_file'):
            out_name = Path(gen.output_file).name
            gen.output_file = job_dir / out_name

        # run generation
        gen.generate()

        # collect generated files from job_dir
        # if generator wrote to other dirs, also try to copy common generated locations
        possible_dirs = [Path("generated_code"), Path("generated_sql"), job_dir]
        for src in possible_dirs:
            if src.exists():
                for f in src.rglob("*"):
                    if f.is_file():
                        dest = job_dir / f.name
                        try:
                            shutil.copyfile(f, dest)
                        except Exception:
                            pass

    else:
        # fallback: write raw puml and a placeholder file
        py_file = job_dir / "puml.txt"
        py_file.write_text(puml, encoding="utf-8")

    readme = job_dir / "README.md"
    readme.write_text("Generated artifacts\n", encoding="utf-8")

    zip_path = STORAGE_DIR / f"{job_id}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for f in job_dir.rglob("*"):
            z.write(f, arcname=f.relative_to(job_dir))

    return zip_path


def run_generation_sync(job_id: str, puml: str, method: str, options: Optional[dict]):
    try:
        JOBS[job_id]["status"] = "running"
        JOBS[job_id]["started_at"] = datetime.utcnow().isoformat() + "Z"
        zip_path = make_artifacts(job_id, puml, method, options)
        JOBS[job_id]["status"] = "done"
        JOBS[job_id]["completed_at"] = datetime.utcnow().isoformat() + "Z"
        JOBS[job_id]["result"] = {
            "download_url": f"http://localhost:{os.getenv('PUML_PORT','8000')}/files/{job_id}.zip"
        }
    except Exception as e:
        JOBS[job_id]["status"] = "error"
        JOBS[job_id]["error"] = str(e)


def run_generation_background(job_id: str, puml: str, method: str, options: Optional[dict]):
    run_generation_sync(job_id, puml, method, options)


@app.post("/generate")
async def generate(req: GenerateRequest, background: BackgroundTasks, authorization: Optional[str] = Header(None)):
    check_auth(authorization)
    job_id = uuid.uuid4().hex
    JOBS[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "request_id": req.request_id,
        "method": req.method,
    }

    if req.sync:
        # run and return inline (small workloads)
        run_generation_sync(job_id, req.puml, req.method, req.options)
        job = JOBS[job_id]
        if job.get("status") == "done":
            # read zip and include files inline (base64) for convenience
            zip_path = STORAGE_DIR / f"{job_id}.zip"
            files = []
            with zipfile.ZipFile(zip_path, "r") as z:
                for name in z.namelist():
                    data = z.read(name)
                    files.append({"name": name, "content_base64": base64.b64encode(data).decode('ascii')})
            return {"status": "done", "job_id": job_id, "result": {"files": files}}
        else:
            raise HTTPException(status_code=500, detail=job.get("error", "unknown"))

    # async: schedule background task and return 202
    background.add_task(run_generation_background, job_id, req.puml, req.method, req.options)
    return {"status": "accepted", "job_id": job_id, "status_url": f"/status/{job_id}"}


@app.get("/pair-code")
async def pair_code(request: Request, authorization: Optional[str] = Header(None)):
    """Generate a one-time pairing code. This endpoint is restricted to requests originating from localhost.

    Admin should call this locally (e.g. curl http://127.0.0.1:8000/pair-code) to obtain a code and give it to the client (extension) to pair.
    """
    client_host = request.client.host if request.client else None
    if client_host not in ("127.0.0.1", "::1", "localhost"):
        raise HTTPException(status_code=403, detail="pair-code generation allowed from localhost only")
    code = generate_pair_code()
    return {"pair_code": code, "ttl": PAIR_CODE_TTL}


@app.post("/pair")
async def pair(payload: dict, request: Request):
    """Exchange a one-time pairing code for the server token.

    Client (extension) should POST {"code":"..."} to this endpoint. Server checks Origin header is allowed and code validity.
    """
    cleanup_pair_codes()
    origin = request.headers.get("origin")
    if origin not in ALLOW_ORIGINS:
        raise HTTPException(status_code=403, detail="Origin not allowed")
    code = payload.get("code") if isinstance(payload, dict) else None
    if not code or code not in PAIR_CODES:
        raise HTTPException(status_code=400, detail="Invalid or expired pair code")
    # consume code
    del PAIR_CODES[code]
    return {"token": SERVER_TOKEN}


@app.post("/receive")
async def receive(payload: dict, authorization: Optional[str] = Header(None)):
    """Receive raw PlantUML text and print it to server console (for debugging/inspection).

    Payload: { "puml": "..." }
    Requires Authorization header same as other endpoints.
    """
    check_auth(authorization)
    puml = None
    if isinstance(payload, dict):
        puml = payload.get("puml")
    if not puml:
        raise HTTPException(status_code=400, detail="missing puml in payload")
    # Print raw PUML to stdout for inspection
    print("\n--- Received PlantUML ---\n")
    try:
        print('Incoming payload keys:', list(payload.keys()) if isinstance(payload, dict) else type(payload))
    except Exception:
        pass
    print(puml)
    print("\n--- End PlantUML ---\n")
    # Debug: show sys.path so we can diagnose import issues
    try:
        print("sys.path:")
        for p in sys.path:
            print("  ", p)
    except Exception:
        pass
    # Prefer plugin-provided diagram type if available
    diagram_type_hint = None
    languages_hint = None
    try:
        if isinstance(payload, dict):
            diagram_type_hint = payload.get('diagramType') or payload.get('diagram_type')
            languages_hint = payload.get('languages') or payload.get('langs')
    except Exception:
        diagram_type_hint = None

    if diagram_type_hint:
        try:
            puml2json = importlib.import_module('puml2json')
            parsed = None
            if diagram_type_hint == 'classes':
                parser = puml2json.PlantUMLParser()
                parsed = parser.parse_content(puml)
                if parsed and parsed.get('classes'):
                    print('\n--- forced puml2json class parser output ---\n')
                    print(json.dumps(parsed, ensure_ascii=False, indent=2))
                    job_id, parsed_file = persist_parsed_result(parsed, puml)
                    plugin_result = None
                    if diagram_type_hint and parsed_file:
                        plugin_result = run_plugin_runner_checked(parsed_file, diagram_type_hint, languages_hint)
                        print('plugin_runner result:', plugin_result)
                    return {"status": "ok", "result": parsed, "job_id": job_id, "plugin": plugin_result}
            elif diagram_type_hint == 'database':
                parser = puml2json.DatabaseDiagramParser()
                parsed = parser.parse(puml)
                if parsed and parsed.get('tables'):
                    print('\n--- forced puml2json database parser output ---\n')
                    print(json.dumps(parsed, ensure_ascii=False, indent=2))
                    job_id, parsed_file = persist_parsed_result(parsed, puml)
                    plugin_result = None
                    if diagram_type_hint and parsed_file:
                        plugin_result = run_plugin_runner_checked(parsed_file, diagram_type_hint, languages_hint)
                        print('plugin_runner result:', plugin_result)
                    return {"status": "ok", "result": parsed, "job_id": job_id, "plugin": plugin_result}
            elif diagram_type_hint == 'deployment':
                parser = puml2json.DeploymentDiagramParser()
                parsed = parser.parse(puml)
                if parsed and (parsed.get('nodes') or parsed.get('connections')):
                    print('\n--- forced puml2json deployment parser output ---\n')
                    print(json.dumps(parsed, ensure_ascii=False, indent=2))
                    job_id, parsed_file = persist_parsed_result(parsed, puml)
                    plugin_result = None
                    if diagram_type_hint and parsed_file:
                        plugin_result = run_plugin_runner_checked(parsed_file, diagram_type_hint, languages_hint)
                        print('plugin_runner result:', plugin_result)
                    return {"status": "ok", "result": parsed, "job_id": job_id, "plugin": plugin_result}
        except HTTPException:
            raise
        except Exception:
            # ignore and continue to general parsing
            traceback.print_exc()
    # First try to parse in-process using the local puml2json module (faster, reliable)
    # prefer the new puml_service wrapper (clean function interface)
    try:
        import puml_service
        result = puml_service.parse_puml_to_json(puml)
        print("\n--- puml_service output ---\n")
        try:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        except Exception:
            print(result)
        # Additional debug: show result type
        try:
            print("puml_service result type:", type(result))
        except Exception:
            pass
        # Persist parsed JSON and raw PUML for inspection
        job_id, parsed_file = persist_parsed_result(result, puml)
        # Optionally run plugin_runner if diagram type / languages provided in payload
        diagram_type = None
        languages = None
        try:
            # payload variable is available in this scope
            diagram_type = payload.get('diagramType') or payload.get('diagram_type')
            languages = payload.get('languages') or payload.get('langs')
        except Exception:
            pass
        plugin_result = None
        if diagram_type and parsed_file:
            plugin_result = run_plugin_runner_checked(parsed_file, diagram_type, languages)
            print("plugin_runner result:", plugin_result)
        elif diagram_type and not parsed_file:
            plugin_result = {"status":"skipped","reason":"parsed file not available"}
        return {"status": "ok", "result": result, "job_id": job_id, "plugin": plugin_result}
    except HTTPException:
        raise
    except Exception:
        print("\n--- puml_service import failed, falling back ---\n")
        traceback.print_exc()
        # fallback: try old in-process puml2json import
        try:
            puml2json = importlib.import_module('puml2json')
            diagram_type = puml2json.detect_diagram_type(puml)
            if diagram_type == 'class':
                parser = puml2json.PlantUMLParser()
                result = parser.parse_content(puml)
            elif diagram_type == 'deployment':
                parser = puml2json.DeploymentDiagramParser()
                result = parser.parse(puml)
            elif diagram_type == 'database':
                parser = puml2json.DatabaseDiagramParser()
                result = parser.parse(puml)
            else:
                result = {"error": "unknown diagram type"}

            out = json.dumps(result, ensure_ascii=False, indent=2)
            print("\n--- puml2json (in-process) output ---\n")
            print(out)
            # Persist parsed JSON and raw PUML
            job_id, parsed_file = persist_parsed_result(result, puml)
            diagram_type = None
            languages = None
            try:
                diagram_type = payload.get('diagramType') or payload.get('diagram_type')
                languages = payload.get('languages') or payload.get('langs')
            except Exception:
                pass
            plugin_result = None
            if diagram_type and parsed_file:
                plugin_result = run_plugin_runner_checked(parsed_file, diagram_type, languages)
                print("plugin_runner result:", plugin_result)
            elif diagram_type and not parsed_file:
                plugin_result = {"status":"skipped","reason":"parsed file not available"}
            return {"status": "ok", "result": result, "job_id": job_id, "plugin": plugin_result}
        except HTTPException:
            raise
        except Exception as e:
            print("\n--- puml2json in-process failed ---\n")
            print(str(e))
            traceback.print_exc()
            # fallback to subprocess invocation (unbuffered)
            puml2json_path = Path(__file__).resolve().parent.parent / 'puml2json.py'
            if not puml2json_path.exists():
                return {"status": "ok", "warning": "puml2json.py not found and in-process import failed"}

            try:
                proc = subprocess.run([sys.executable, '-u', str(puml2json_path)], input=puml.encode('utf-8'), capture_output=True, timeout=30)
            except subprocess.TimeoutExpired:
                raise HTTPException(status_code=500, detail="puml2json timed out")
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

            stdout = proc.stdout.decode('utf-8', errors='replace') if proc.stdout else ''
            stderr = proc.stderr.decode('utf-8', errors='replace') if proc.stderr else ''

            print("\n--- puml2json stdout (subprocess) ---\n")
            print(stdout)
            if stderr:
                print("\n--- puml2json stderr (subprocess) ---\n")
                print(stderr)

            if proc.returncode != 0:
                raise HTTPException(status_code=500, detail=f"puml2json failed: {stderr[:200]}")

            try:
                result = json.loads(stdout)
                # Persist parsed JSON and raw PUML
                job_id, parsed_file = persist_parsed_result(result, puml)
                return {"status": "ok", "result": result, "job_id": job_id}
            except Exception:
                # still persist raw stdout for inspection
                try:
                    job_id = uuid.uuid4().hex
                    job_dir = STORAGE_DIR / job_id
                    job_dir.mkdir(parents=True, exist_ok=True)
                    (job_dir / "output.txt").write_text(stdout, encoding="utf-8")
                    (job_dir / "input.puml").write_text(puml, encoding="utf-8")
                    print(f"Saved raw output to {job_dir / 'output.txt'}")
                except Exception as _e:
                    print("Failed to persist subprocess output:", _e)
                return {"status": "ok", "output": stdout, "note": "output not valid JSON", "job_id": job_id}


@app.get("/status/{job_id}")
async def status(job_id: str, authorization: Optional[str] = Header(None)):
    # require auth
    check_auth(authorization)
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job


@app.get("/files/{job_id}.zip")
async def get_zip(job_id: str, request: Request, authorization: Optional[str] = Header(None)):
    # require token
    check_auth(authorization)
    zip_path = STORAGE_DIR / f"{job_id}.zip"
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(path=str(zip_path), filename=f"{job_id}.zip")


@app.get("/download/{job_id}")
async def download_generated(job_id: str, authorization: Optional[str] = Header(None)):
    """Download generated artifacts for a job.

    - If exactly one generated file exists, return it directly.
    - If multiple files exist, return a zip archive.
    """
    check_auth(authorization)
    files = collect_generated_files(job_id)
    if not files:
        raise HTTPException(status_code=404, detail="generated files not found")

    if len(files) == 1:
        file_path = files[0]
        return FileResponse(path=str(file_path), filename=file_path.name)

    bundle_path = STORAGE_DIR / job_id / f"{job_id}_generated.zip"
    run_root = files[0].parent
    with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for file_path in files:
            try:
                arcname = str(file_path.relative_to(run_root))
            except Exception:
                arcname = file_path.name
            z.write(file_path, arcname=arcname)

    return FileResponse(path=str(bundle_path), filename=bundle_path.name)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PUML_PORT", "8000"))
    print("Server token:", SERVER_TOKEN)
    uvicorn.run("server:app", host="127.0.0.1", port=port, reload=True)
