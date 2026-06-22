#!/usr/bin/env python3
"""Session 10: Computer-Use Agent — Web Dashboard

A FastAPI web dashboard for running and monitoring the Computer-Use Agent.
Features:
  - Real-time log streaming via WebSocket
  - Task presets for Calculator, Gedit, Obsidian
  - Layer selection (Auto / Deterministic / A11y / Vision)
  - Run history with status tracking
  - Live result display with cascade path visualization

Run:
    cd S9SharedCode/code
    uv run python dashboard.py
"""

from __future__ import annotations

import asyncio
import io
import json
import os
import sys
import time
import uuid
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Ensure our code dir is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from computer.skill import ComputerSkill
from schemas import NodeSpec

app = FastAPI(title="Computer-Use Agent Dashboard", version="1.0.0")

# Serve static files (CSS, JS)
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ── State ────────────────────────────────────────────────────────────────────

RUN_HISTORY: list[dict] = []
ACTIVE_WEBSOCKETS: list[WebSocket] = []
CURRENT_RUN: dict[str, Any] | None = None
ACTIVE_TASK: asyncio.Task | None = None


# ── Models ───────────────────────────────────────────────────────────────────

class TaskRequest(BaseModel):
    app: str = "Calculator"
    goal: str = "Calculate 7 times 8"
    force_path: str | None = None  # None = auto, "deterministic", "a11y", "vision"


# ── WebSocket broadcast ─────────────────────────────────────────────────────

async def broadcast(msg: dict):
    """Send a JSON message to all connected WebSocket clients."""
    dead = []
    for ws in ACTIVE_WEBSOCKETS:
        try:
            await ws.send_json(msg)
        except Exception:
            dead.append(ws)
    for ws in dead:
        ACTIVE_WEBSOCKETS.remove(ws)


class LogCapture(io.StringIO):
    """Intercepts print() output and broadcasts to WebSocket clients."""
    def __init__(self, loop: asyncio.AbstractEventLoop):
        super().__init__()
        self._loop = loop
        self._real_stdout = sys.stdout

    def write(self, s: str):
        self._real_stdout.write(s)
        if s.strip():
            asyncio.run_coroutine_threadsafe(
                broadcast({"type": "log", "text": s.rstrip(), "ts": time.time()}),
                self._loop
            )
        return len(s)

    def flush(self):
        self._real_stdout.flush()


# ── Task runner ──────────────────────────────────────────────────────────────

async def run_task(req: TaskRequest, run_id: str):
    """Execute a ComputerSkill task and stream logs via WebSocket."""
    global CURRENT_RUN

    loop = asyncio.get_event_loop()
    log_capture = LogCapture(loop)

    CURRENT_RUN = {
        "id": run_id,
        "app": req.app,
        "goal": req.goal,
        "force_path": req.force_path,
        "status": "running",
        "started_at": datetime.now().isoformat(),
        "result": None,
    }
    RUN_HISTORY.append(CURRENT_RUN)

    await broadcast({
        "type": "status",
        "run_id": run_id,
        "status": "running",
        "app": req.app,
        "goal": req.goal,
    })

    old_stdout = sys.stdout
    sys.stdout = log_capture

    try:
        from flow import Executor
        from persistence import SessionStore
        from schemas import AgentResult

        executor = Executor()
        # Run the full agent planning and execution loop
        final_answer = await executor.run(req.goal, session_id=run_id)

        # Retrieve the graph to extract precise execution metrics
        store = SessionStore(run_id)
        g = store.read_graph()

        success = False
        path = "unknown"
        turns = 0
        error_msg = None

        if g is not None:
            # Inspect the executed computer/browser skill nodes
            for nid in g.nodes:
                d = g.nodes[nid]
                if d.get("skill") in ("computer", "browser"):
                    res = d.get("result")
                    if res:
                        success = res.success
                        path = res.output.get("path", "unknown")
                        turns = res.output.get("turns", 0)
                        error_msg = res.error
                        break
            else:
                success = len(final_answer) > 0
                turns = len(g.nodes)
        else:
            success = len(final_answer) > 0

        CURRENT_RUN["status"] = "success" if success else "failed"
        CURRENT_RUN["result"] = {
            "success": success,
            "path": path,
            "turns": turns,
            "content": final_answer,
            "app": req.app,
            "error": error_msg or (None if success else "Task failed or rejected by critic"),
        }
        CURRENT_RUN["completed_at"] = datetime.now().isoformat()
    except Exception as e:
        CURRENT_RUN["status"] = "error"
        CURRENT_RUN["result"] = {"success": False, "error": str(e), "path": "error", "turns": 0, "content": ""}
        CURRENT_RUN["completed_at"] = datetime.now().isoformat()
    finally:
        sys.stdout = old_stdout
        global ACTIVE_TASK
        ACTIVE_TASK = None

    await broadcast({
        "type": "result",
        "run_id": run_id,
        **CURRENT_RUN,
    })

    CURRENT_RUN = None


# ── API routes ───────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = Path(__file__).parent / "static" / "dashboard.html"
    return html_path.read_text()


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    global CURRENT_RUN, ACTIVE_TASK
    await ws.accept()
    ACTIVE_WEBSOCKETS.append(ws)

    # Send current state
    await ws.send_json({
        "type": "init",
        "history": RUN_HISTORY[-20:],
        "current_run": CURRENT_RUN,
    })

    try:
        while True:
            data = await ws.receive_json()
            if data.get("action") == "run_task":
                if CURRENT_RUN is not None:
                    await ws.send_json({"type": "error", "text": "A task is already running."})
                    continue
                req = TaskRequest(**data.get("task", {}))
                run_id = f"run_{uuid.uuid4().hex[:8]}"
                ACTIVE_TASK = asyncio.create_task(run_task(req, run_id))
            elif data.get("action") == "stop_task":
                if ACTIVE_TASK and not ACTIVE_TASK.done():
                    ACTIVE_TASK.cancel()
                    import subprocess
                    subprocess.run(["pkill", "-f", "test_task"], capture_output=True)
                    subprocess.run(["pkill", "-9", "-f", "sandbox_chrome_profile"], capture_output=True)
                    subprocess.run(["killall", "-9", "obsidian", "gedit"], capture_output=True)
                    if CURRENT_RUN:
                        CURRENT_RUN["status"] = "cancelled"
                        CURRENT_RUN["result"] = {"success": False, "error": "Task stopped by user", "path": "error", "turns": 0, "content": ""}
                        CURRENT_RUN["completed_at"] = datetime.now().isoformat()
                    await broadcast({
                        "type": "result",
                        "run_id": CURRENT_RUN["id"] if CURRENT_RUN else "unknown",
                        **(CURRENT_RUN or {}),
                    })
                    CURRENT_RUN = None
                    ACTIVE_TASK = None
    except WebSocketDisconnect:
        if ws in ACTIVE_WEBSOCKETS:
            ACTIVE_WEBSOCKETS.remove(ws)


@app.get("/api/history")
async def get_history():
    return {"runs": RUN_HISTORY[-50:]}


@app.get("/api/presets")
async def get_presets():
    return {
        "presets": [
            {
                "id": "calc_det",
                "name": "Calculator (Deterministic)",
                "icon": "🧮",
                "app": "Calculator",
                "goal": "Calculate 143423 times 23",
                "force_path": None,
                "description": "Layer 2a: deterministic hotkey clicks. $0 cost.",
                "tags": ["Layer 2a", "Zero LLM", "$0"],
            },
            {
                "id": "calc_vision",
                "name": "Calculator (Vision)",
                "icon": "👁️",
                "app": "Calculator",
                "goal": "Using vision, calculate 7 times 8 on the calculator",
                "force_path": "vision",
                "description": "Layer 3: screenshot + VLM. Forces vision path.",
                "tags": ["Layer 3", "Vision", "VLM"],
            },
            {
                "id": "gedit_save",
                "name": "Gedit Save File",
                "icon": "📝",
                "app": "gedit",
                "goal": "Write 'The calculated result is 3298729' and save it to /home/mani_radhakrishnan/sandbox_session10/mr_s10_03.txt",
                "force_path": None,
                "description": "Layer 2a: deterministic Ctrl+L save. Zero LLM.",
                "tags": ["Layer 2a", "GTK", "Save"],
            },
            {
                "id": "obsidian_cdp",
                "name": "Obsidian (CDP Page Tool)",
                "icon": "💎",
                "app": "Obsidian",
                "goal": "Create a note titled 'mr_s10_result' with content 'The calculated result is 3298729' in Obsidian",
                "force_path": None,
                "description": "Layer 2a: Electron CDP page tool. JavaScript execution.",
                "tags": ["Layer 2a", "Electron", "CDP"],
            },
            {
                "id": "workflow",
                "name": "Multi-App Workflow",
                "icon": "🔗",
                "app": "Calculator",
                "goal": "Calculate 42 times 58",
                "force_path": None,
                "description": "Start of Calculator→Gedit→Obsidian chain.",
                "tags": ["Multi-app", "Pipeline", "Chain"],
            },
            {
                "id": "puzzle_game",
                "name": "Visual Sliding Puzzle",
                "icon": "🧩",
                "app": "Puzzle",
                "goal": "Using vision, identify the numbered tile that is out of order on the sliding puzzle grid, click it to restore order (1-8 with the empty slot in the bottom-right), and verify that the status says Solved",
                "force_path": "vision",
                "description": "Task 4: Canvas-rendered visual Sliding Puzzle. Forces Layer 3 vision.",
                "tags": ["Layer 3", "Vision", "Canvas", "Puzzle"],
            },
            {
                "id": "email_draft",
                "name": "Email Draft Composer",
                "icon": "📧",
                "app": "Chrome",
                "goal": "Write draft to 'student@example.com', subject 'Session 10 Submission', body 'Everything works perfectly', click Save Draft, and verify saving",
                "force_path": "a11y",
                "description": "Task 5: Message draft composition with verification. Exercises Layer 2b.",
                "tags": ["Layer 2b", "A11y", "Form", "Verification"],
            },
        ]
    }


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    print("🖥️  Computer-Use Agent Dashboard")
    print("   Open http://localhost:8110 in your browser")
    uvicorn.run(app, host="0.0.0.0", port=8110)
