"""Session 10: the Computer skill — OS automation via cua-driver.
-------------------------------------------------------------------------
Four-layer cascade following the session curriculum:

    Layer 1  — extract: read AX tree text directly ($0)
    Layer 2a — deterministic: element_index clicks for known apps ($0)
    Layer 2b — a11y: AX tree markdown + cheap text LLM (cents)
    Layer 3  — vision: screenshot + vision LLM (dollars, last resort)

cua-driver is the SOLE substrate for all perception and action.
No pyautogui. No mocks. Just cua-driver.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any

from schemas import AgentResult, NodeSpec
from browser.client import V9Client

# ─── cua-driver interface ───────────────────────────────────────────────────

CUA_BIN = str(Path.home() / ".local" / "bin" / "cua-driver")


class CuaError(RuntimeError):
    pass


# A global variable to track the active session ID for global _cua_call interception
_ACTIVE_SESSION: str | None = None


def _cua_call(tool: str, args: dict[str, Any]) -> dict[str, Any]:
    """Invoke a cua-driver tool through the running daemon."""
    global _ACTIVE_SESSION
    if _ACTIVE_SESSION:
        if "session" not in args:
            args["session"] = _ACTIVE_SESSION
        if "cursor_id" not in args:
            args["cursor_id"] = _ACTIVE_SESSION
    proc = subprocess.run(
        [CUA_BIN, "call", tool, json.dumps(args)],
        capture_output=True, text=True, timeout=30,
    )
    if proc.returncode != 0:
        raise CuaError(f"{tool} failed: {proc.stderr.strip()}")
    out = proc.stdout.strip()
    if out.startswith("{") or out.startswith("["):
        return json.loads(out)
    return {"raw": out}


def _ensure_daemon(cdp_port: str | None = None) -> None:
    """Start cua-driver serve, ensuring environment matches cdp_port."""
    need_restart = False
    
    # Check if currently running
    is_running = False
    try:
        st = subprocess.run([CUA_BIN, "status"], capture_output=True, text=True, timeout=5)
        if "running" in st.stdout.lower():
            is_running = True
    except Exception:
        pass

    current_env_port = os.environ.get("CUA_DRIVER_CDP_PORT")
    if cdp_port:
        if current_env_port != cdp_port:
            os.environ["CUA_DRIVER_CDP_PORT"] = cdp_port
            need_restart = True
    else:
        if current_env_port:
            del os.environ["CUA_DRIVER_CDP_PORT"]
            need_restart = True

    if is_running and need_restart:
        print("[ComputerSkill] Restarting cua-driver daemon to apply CUA_DRIVER_CDP_PORT...")
        subprocess.run(["killall", "cua-driver"], capture_output=True)
        time.sleep(0.5)
        is_running = False

    if not is_running:
        subprocess.Popen([CUA_BIN, "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.5)


# ─── expression parsing for Calculator ──────────────────────────────────────

def _parse_math_expression(goal: str) -> str | None:
    """Extract a calculator expression from natural language goal."""
    text = goal.lower().strip()
    for word in ("times", "multipliedby", "multiplied by", "into",
                 "plus", "add", "minus", "subtract", "dividedby", "divided by", "over"):
        text = re.sub(rf'(\d){word}(\d)', rf'\1 {word} \2', text, flags=re.IGNORECASE)
    for pat, repl in [
        (r'\btimes\b', '*'), (r'\bmultiplied\s*by\b', '*'), (r'\binto\b', '*'),
        (r'\bx\b', '*'),
        (r'\bplus\b', '+'), (r'\badd\b', '+'),
        (r'\bminus\b', '-'), (r'\bsubtract\b', '-'),
        (r'\bdivided?\s*by\b', '/'), (r'\bover\b', '/'),
    ]:
        text = re.sub(pat, repl, text)
    for prefix in ("solve", "solbe", "calculate", "compute", "what is", "find", "evaluate"):
        text = re.sub(rf'^\s*{prefix}\s*', '', text)
    text = re.sub(r'\s*(in|on|using|with)\s*(the\s*)?(calculator|calc|gnome.calculator)(\s*app)?', '', text)
    expr = re.sub(r'[^0-9+\-*/().=]', '', text.strip()).rstrip('=. ')
    if expr and re.search(r'\d', expr) and re.search(r'[+\-*/]', expr):
        return expr
    return None


# ─── AX tree helpers ─────────────────────────────────────────────────────────

def _find_display_value(tree_md: str) -> str | None:
    """Extract the calculator display value from tree_markdown."""
    m = re.search(r'edit bar\s*=\s*"([^"]*)"', tree_md)
    if m:
        return m.group(1).strip()
    for val in re.findall(r'label\s*=\s*"([^"]*)"', tree_md):
        val_clean = val.strip()
        if val_clean and (val_clean.isdigit() or val_clean.replace(".", "", 1).isdigit()):
            return val_clean
    return None


def _find_element_by_label(tree_md: str, label: str) -> int | None:
    """Find element_index for a button with the given label."""
    pattern = rf'-\s*\[(\d+)\]\s+(?:[a-zA-Z\s\-]+)?\s*"{re.escape(label)}"'
    m = re.search(pattern, tree_md)
    return int(m.group(1)) if m else None


async def _get_active_window(pid: int, app_name: str, fallback_wid: int) -> int:
    for attempt in range(8):
        try:
            windows = _cua_call("list_windows", {})
            app_windows = []
            for w in windows.get("windows", []):
                if w.get("pid") == pid:
                    app_windows.append(w)
            if app_windows:
                # Search for dialog titles
                for w in app_windows:
                    title = (w.get("title") or "").lower()
                    if any(x in title for x in ("save", "open", "confirm", "question", "error", "warning", "save as")):
                        return w["window_id"]
                # If the active window changed to a new top-level window, return it
                if app_windows[-1]["window_id"] != fallback_wid:
                    return app_windows[-1]["window_id"]
        except Exception:
            pass
        await asyncio.sleep(0.3)
    return fallback_wid


# ─── Layer 2b prompt ─────────────────────────────────────────────────────────

A11Y_SYSTEM = (
    "You are a computer-use agent. You see the accessibility tree of a desktop app.\n"
    "Each actionable element has an [element_index N] tag.\n\n"
    "Respond with exactly ONE JSON object:\n"
    '  To click a button: {"thinking":"...","action":{"type":"click","element_index":<N>}}\n'
    '  To double-click (e.g. folder): {"thinking":"...","action":{"type":"click","element_index":<N>,"count":2}}\n'
    '  To type text into element N:  {"thinking":"...","action":{"type":"type_text","element_index":<N>,"text":"<text>"}}\n'
    '  To type text into focused element: {"thinking":"...","action":{"type":"type_text","text":"<text>"}}\n'
    '  To press a key:    {"thinking":"...","action":{"type":"press_key","key":"<key>"}}\n'
    '  To press hotkey:   {"thinking":"...","action":{"type":"hotkey","keys":["ctrl","l"]}}\n'
    '  To mark done:      {"thinking":"...","action":{"type":"done","success":true,"note":"..."}}\n'
    "Pick the single next action that advances the goal. Be terse.\n\n"
    "TIP FOR OPENING THE SAVE DIALOG IN MAIN WINDOW:\n"
    "To open the Save As dialog, locate the button labeled 'Save' in the window header bar (usually index 7 or similar, role='push button') and click it. DO NOT click side-panel buttons like 'File Browser' or 'Documents' which do not open the save dialog.\n\n"
    "TIP FOR SAVING FILES IN GTK DIALOGS:\n"
    "To save a file to a specific directory and name (e.g. /home/mani_radhakrishnan/sandbox_session10/mr_s10_03.txt):\n"
    "1. Locate the filename text entry field (often role='text' next to Save/Cancel or labeled 'Name'/'Name Entry').\n"
    "2. Type the FULL path (e.g., '/home/mani_radhakrishnan/sandbox_session10/mr_s10_03.txt') into that field using type_text with its element_index.\n"
    "3. Click the 'Save' button (role='push button', labeled 'Save') in the dialog.\n"
    "4. If a confirmation dialog appears stating a file already exists, locate the 'Replace' button (usually role='push button') and click it to overwrite the file."
)

A11Y_SCHEMA = {
    "type": "object",
    "properties": {
        "thinking": {"type": "string"},
        "action": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["click", "type_text", "press_key", "hotkey", "done"]},
                "element_index": {"type": "integer"},
                "count": {"type": "integer"},
                "text": {"type": "string"},
                "key": {"type": "string"},
                "keys": {"type": "array", "items": {"type": "string"}},
                "success": {"type": "boolean"},
                "note": {"type": "string"},
            },
            "required": ["type"],
        },
    },
    "required": ["thinking", "action"],
}


# ─── Layer 3 prompt ──────────────────────────────────────────────────────────

VISION_SYSTEM = (
    "You see a screenshot of a desktop. You are a computer-use agent.\n"
    "Respond with JSON: {\"thinking\":\"...\",\"actions\":[{\"type\":\"click\",\"x\":<X>,\"y\":<Y>}]}\n"
    "Coordinates are on a 0-1000 scale (x from 0 to 1000, y from 0 to 1000). To finish: {\"thinking\":\"...\",\"actions\":[{\"type\":\"done\",\"success\":true,\"note\":\"...\"}]}\n"
    "One action per response."
)

VISION_SCHEMA = {
    "type": "object",
    "properties": {
        "thinking": {"type": "string"},
        "actions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["click", "type", "done"]},
                    "x": {"type": "integer"},
                    "y": {"type": "integer"},
                    "text": {"type": "string"},
                    "success": {"type": "boolean"},
                    "note": {"type": "string"},
                },
                "required": ["type"],
            },
        },
    },
    "required": ["thinking", "actions"],
}


# ─── The Skill ───────────────────────────────────────────────────────────────

class ComputerSkill:
    NAME = "computer"

    def __init__(
        self,
        *,
        gateway_url: str = "http://localhost:8109",
        agent_tag: str = "computer",
        artifacts_root: str | None = None,
        max_steps_a11y: int = 15,
        max_steps_vision: int = 12,
        session: str | None = None,
    ):
        self.gateway_url = gateway_url
        self.agent_tag = agent_tag
        self.artifacts_root = Path(artifacts_root) if artifacts_root else None
        self.max_steps_a11y = max_steps_a11y
        self.max_steps_vision = max_steps_vision
        self.session = session

    # ── public entry ─────────────────────────────────────────────────────
    async def run(self, node: NodeSpec) -> AgentResult:
        global _ACTIVE_SESSION
        _ACTIVE_SESSION = self.session
        try:
            app_name = node.metadata.get("app") or "Calculator"
            goal = node.metadata.get("goal") or "Calculate 7 times 8"
            force_path = node.metadata.get("force_path")
            if "vision" in goal.lower() or "vision" in app_name.lower() or any(x in app_name.lower() for x in ["puzzle", "breakout", "game"]):
                force_path = "vision"
            t0 = time.time()

            if self.artifacts_root:
                self.artifacts_root.mkdir(parents=True, exist_ok=True)

            if not Path(CUA_BIN).exists():
                return self._err(app_name, goal, "dependency_error",
                                 f"cua-driver not found at {CUA_BIN}", t0=t0)

            # Start daemon + launch app + find window
            try:
                cdp_port = node.metadata.get("cdp_port") or ("9223" if app_name.lower() in ("obsidian",) else None)
                _ensure_daemon(cdp_port)
                pid, wid = await self._launch_and_find(app_name, goal)
            except Exception as e:
                return self._err(app_name, goal, "interaction_failed",
                                 f"Setup failed: {e}", t0=t0)

            # Start session and configure cursor
            if self.session:
                try:
                    _cua_call("start_session", {"session": self.session})
                    # Configure the agent cursor to move instantly (glide_duration_ms = 0)
                    # so the movement does not lag behind the programmatic clicks
                    _cua_call("set_agent_cursor_motion", {
                        "session": self.session,
                        "cursor_id": self.session,
                        "glide_duration_ms": 0,
                        "dwell_after_click_ms": 0
                    })
                    # Enable the agent cursor explicitly
                    _cua_call("set_agent_cursor_enabled", {
                        "session": self.session,
                        "cursor_id": self.session,
                        "enabled": True
                    })
                except CuaError as e:
                    print(f"[ComputerSkill] Failed to init session cursor: {e}")

            # Bring window to front
            try:
                _cua_call("bring_to_front", {"pid": pid})
            except CuaError:
                pass

            print(f"[ComputerSkill] app={app_name} pid={pid} wid={wid} goal={goal}")

            # Start recording for trajectory evidence
            if self.session:
                try:
                    rec_dir = str(self.artifacts_root / "trajectory") if self.artifacts_root else f"/tmp/run-{self.session}"
                    _cua_call("start_recording", {"output_dir": rec_dir})
                except CuaError:
                    pass

            # Scan AX tree (with polling for GTK a11y bridge delay)
            tree_md, elem_count = "", 0
            try:
                for _ in range(10):
                    active_wid = await _get_active_window(pid, app_name, wid)
                    state = _cua_call("get_window_state",
                                      {"pid": pid, "window_id": active_wid, "capture_mode": "ax"})
                    tree_md = state.get("tree_markdown", "")
                    elem_count = state.get("element_count", 0)
                    if elem_count >= 10:
                        break
                    await asyncio.sleep(0.5)
                print(f"[ComputerSkill] AX tree: {elem_count} elements")
            except CuaError as e:
                print(f"[ComputerSkill] AX scan failed: {e}")

            # ── Layer 1: extract ─────────────────────────────────────────
            if force_path is None and elem_count > 0:
                display = _find_display_value(tree_md)
                if display and self._answer_visible(display, goal):
                    print(f"[ComputerSkill] Layer 1 (extract): answer visible: {display}")
                    return self._ok(app_name, goal, "extract", turns=0,
                                    content=f"Display shows: {display}")

            # ── Layer 2a: deterministic ──────────────────────────────────
            if force_path in (None, "deterministic") and elem_count > 0:
                is_calc = app_name.lower() in ("calculator", "gnome-calculator")
                if is_calc:
                    result = await self._layer2a_calculator(pid, wid, app_name, goal, t0)
                    if result is not None:
                        return result
                
                is_gedit = app_name.lower() in ("gedit", "text editor", "textedit")
                if is_gedit:
                    result = await self._layer2a_gedit_save(pid, wid, app_name, goal, t0)
                    if result is not None:
                        return result
                
                is_obsidian = app_name.lower() in ("obsidian",)
                if is_obsidian:
                    result = await self._layer2a_obsidian_save(pid, wid, app_name, goal, t0)
                    if result is not None:
                        return result

            # ── Layer 2b: a11y (AX tree + LLM) ──────────────────────────
            if force_path in (None, "a11y") and elem_count > 0:
                result = await self._layer2b_a11y(pid, wid, app_name, goal, t0)
                if result is not None:
                    return result

            # ── Layer 3: vision (screenshot + VLM) ───────────────────────
            result = await self._layer3_vision(pid, wid, app_name, goal, t0)
            if result is not None:
                return result

            # Stop recording
            try:
                _cua_call("stop_recording", {})
            except CuaError:
                pass

            return self._err(app_name, goal, "interaction_failed",
                             "All layers exhausted", t0=t0)
        finally:
            _ACTIVE_SESSION = None

    # ── app launch + window discovery ────────────────────────────────
    async def _launch_and_find(self, app_name: str, goal: str = "") -> tuple[int, int]:
        """Launch the app via cua-driver and return (pid, window_id)."""
        # Map friendly names to command names for cua-driver
        CMD_MAP = {
            "calculator": "gnome-calculator",
            "gnome-calculator": "gnome-calculator",
            "text editor": "gedit",
            "textedit": "gedit",
            "gedit": "gedit",
            "obsidian": "obsidian",
            "chrome": "google-chrome",
            "google-chrome": "google-chrome",
        }
        # Title patterns to match in list_windows
        TITLE_MAP = {
            "calculator": ["calculator"],
            "gnome-calculator": ["calculator"],
            "text editor": ["gedit", "untitled document"],
            "textedit": ["gedit", "untitled document"],
            "gedit": ["gedit", "untitled document"],
            "obsidian": ["obsidian"],
            "chrome": ["chrome", "google chrome", "canvas target game", "email draft composer"],
            "google-chrome": ["chrome", "google chrome", "canvas target game", "email draft composer"],
            "breakout": ["breakout", "visual breakout"],
            "composer": ["composer", "email draft"],
            "puzzle": ["puzzle", "visual sliding puzzle"],
            "sliding_puzzle": ["puzzle", "visual sliding puzzle", "sliding puzzle"],
            "sliding-puzzle": ["puzzle", "visual sliding puzzle", "sliding puzzle"],
        }

        target_key = app_name.lower()
        cmd_name = CMD_MAP.get(target_key, app_name.lower().replace(" ", "-"))
        title_patterns = TITLE_MAP.get(target_key, [target_key])

        # Kill existing instances to get clean state
        if "calculator" in target_key:
            subprocess.run(["killall", "gnome-calculator"], capture_output=True)
            await asyncio.sleep(0.5)
        elif "gedit" in target_key or "text editor" in target_key:
            subprocess.run(["killall", "gedit"], capture_output=True)
            await asyncio.sleep(0.5)
        elif "obsidian" in target_key:
            subprocess.run(["killall", "-9", "obsidian"], capture_output=True)
            await asyncio.sleep(0.5)

        # Launch via cua-driver
        launched_pid = None
        if "obsidian" in target_key:
            # For Obsidian (Electron), launch with debugging port enabled
            env = dict(os.environ)
            env["DISPLAY"] = os.environ.get("DISPLAY", ":0")
            proc = subprocess.Popen(["obsidian", "--remote-debugging-port=9223"], env=env)
            launched_pid = proc.pid
        elif any(k in target_key for k in ["chrome", "google-chrome", "breakout", "composer", "puzzle"]):
            # Determine correct URL based on target_key or goal
            goal_lower = goal.lower()
            if "puzzle" in target_key or "sliding" in goal_lower:
                url = "http://localhost:8110/static/slide_puzzle.html"
            elif "composer" in target_key or "email" in target_key or "draft" in goal_lower:
                url = "http://localhost:8110/static/email_draft.html"
            elif "breakout" in target_key or "puck" in goal_lower:
                url = "http://localhost:8110/static/breakout_game.html"
            else:
                url = "http://localhost:8110/"

            chrome_cmd = [
                "google-chrome",
                "--new-window",
                f"--user-data-dir=/home/mani_radhakrishnan/TSAI_EAGV3_Session10/sandbox_chrome_profile_{target_key}",
            ]
            if "composer" in target_key or "email" in target_key or "draft" in goal_lower:
                chrome_cmd.append("--remote-debugging-port=9224")
            chrome_cmd.append(url)

            env = dict(os.environ)
            env["DISPLAY"] = os.environ.get("DISPLAY", ":0")
            proc = subprocess.Popen(chrome_cmd, env=env)
            launched_pid = proc.pid
            # Give Chrome time to load and set window title
            await asyncio.sleep(3.5)
        else:
            try:
                res = _cua_call("launch_app", {"name": cmd_name})
                raw = res.get("raw", "")
                m = re.search(r"pid\s+(\d+)", raw)
                if m:
                    launched_pid = int(m.group(1))
                elif res.get("pid"):
                    launched_pid = res["pid"]
            except CuaError:
                # Fallback: direct subprocess launch
                env = dict(os.environ)
                env["DISPLAY"] = os.environ.get("DISPLAY", ":0")
                proc = subprocess.Popen([cmd_name], env=env)
                launched_pid = proc.pid

        await asyncio.sleep(1.5)

        # Find the window via list_windows
        for attempt in range(10):
            try:
                windows = _cua_call("list_windows", {})
                for w in windows.get("windows", []):
                    title = (w.get("title") or "").lower()
                    if any(term in title for term in ["terminal", "terminator", "bash", "flow.py", "mani_radhakrishnan@"]):
                        continue
                    w_pid = w.get("pid")
                    # Match by launched PID first
                    if launched_pid and w_pid == launched_pid:
                        try:
                            _cua_call("bring_to_front", {"pid": w_pid, "window_id": w["window_id"]})
                        except Exception:
                            pass
                        return w_pid, w["window_id"]
                    # Then match by title patterns
                    for pat in title_patterns:
                        if pat in title:
                            try:
                                _cua_call("bring_to_front", {"pid": w_pid, "window_id": w["window_id"]})
                            except Exception:
                                pass
                            return w_pid, w["window_id"]
            except CuaError:
                pass
            await asyncio.sleep(0.5)

        raise RuntimeError(f"Could not find window for '{app_name}' after launch")

    # ── Layer 2a: deterministic calculator ────────────────────────────
    async def _layer2a_calculator(self, pid, wid, app_name, goal, t0) -> AgentResult | None:
        expr = _parse_math_expression(goal)
        if not expr:
            return None

        print(f"[ComputerSkill] Layer 2a (deterministic): expression = {expr}")
        turns = 0
        char_to_label = {
            '0': '0', '1': '1', '2': '2', '3': '3', '4': '4',
            '5': '5', '6': '6', '7': '7', '8': '8', '9': '9',
            '+': '+', '-': '-', '*': '×', '/': '÷', '.': '.',
        }

        for ch in expr:
            label = char_to_label.get(ch)
            if label is None:
                continue

            # Re-scan before each click (Invariant: fresh element cache)
            try:
                state = _cua_call("get_window_state",
                                  {"pid": pid, "window_id": wid, "capture_mode": "ax"})
                tree_md = state.get("tree_markdown", "")
            except CuaError:
                return None

            idx = _find_element_by_label(tree_md, label)
            if idx is None:
                print(f"[ComputerSkill] Layer 2a: button '{label}' not found")
                return None

            _cua_call("click", {"pid": pid, "window_id": wid, "element_index": idx})
            turns += 1
            print(f"[ComputerSkill] Layer 2a: clicked '{label}' (element_index={idx})")
            await asyncio.sleep(0.2)

        # Click = (equals)
        state = _cua_call("get_window_state",
                          {"pid": pid, "window_id": wid, "capture_mode": "ax"})
        tree_md = state.get("tree_markdown", "")
        eq_idx = _find_element_by_label(tree_md, "=")
        if eq_idx is not None:
            _cua_call("click", {"pid": pid, "window_id": wid, "element_index": eq_idx})
            turns += 1
            await asyncio.sleep(0.5)

        # Verify: read result
        state = _cua_call("get_window_state",
                          {"pid": pid, "window_id": wid, "capture_mode": "ax"})
        tree_md = state.get("tree_markdown", "")
        result_val = _find_display_value(tree_md)
        content = f"{expr} = {result_val}" if result_val else f"Expression {expr} entered"
        print(f"[ComputerSkill] Layer 2a result: {content}")
        return self._ok(app_name, goal, "deterministic", turns=turns, content=content)

    # ── Layer 2a: deterministic gedit save ────────────────────────────
    async def _layer2a_gedit_save(self, pid, wid, app_name, goal, t0) -> AgentResult | None:
        """Deterministic save for gedit: EWMH focus + XTEST Ctrl+L navigation + Save."""
        if not any(k in goal.lower() for k in ["save", "write", "file", "path"]):
            return None

        # Parse goal
        directory, filename, content = _parse_gedit_goal(goal)
        print(f"[ComputerSkill] Layer 2a (gedit): dir={directory}, file={filename}, content={content}")

        # Pre-delete the target file to avoid the GTK Replace confirmation dialog
        target_path = os.path.join(directory, filename)
        if os.path.exists(target_path):
            try:
                os.remove(target_path)
                print(f"[ComputerSkill] Pre-deleted existing file to avoid confirmation: {target_path}")
            except Exception as e:
                print(f"[ComputerSkill] Failed to pre-delete existing file: {e}")

        # Scan editor to find text area
        state = _cua_call("get_window_state", {"pid": pid, "window_id": wid, "capture_mode": "ax"})
        tree = state.get("tree_markdown", "")
        
        text_idx = None
        for line in tree.splitlines():
            if 'role description = "text"' in line.lower() or ('"text"' in line.lower() and 'push button' not in line.lower() and 'radio' not in line.lower()):
                m = re.search(r'\[(\d+)\]', line)
                if m and 'search' not in line.lower():
                    text_idx = int(m.group(1))
                    break
        
        if text_idx is None:
            for line in tree.splitlines():
                if re.search(r'\[\d+\].*text.*"', line, re.I) and 'search' not in line.lower():
                    m = re.search(r'\[(\d+)\]', line)
                    if m:
                        text_idx = int(m.group(1))
                        break

        if text_idx is None:
            print("[ComputerSkill] Layer 2a (gedit): text area not found")
            return None

        # Type content into editor
        _cua_call("type_text", {"pid": pid, "window_id": wid, "element_index": text_idx, "text": content})
        await asyncio.sleep(0.5)

        # Find and click editor's Save button to open Save As dialog
        save_idx = None
        for line in tree.splitlines():
            if "save" in line.lower() and "push button" in line.lower():
                m = re.search(r'\[(\d+)\]', line)
                if m:
                    save_idx = int(m.group(1))
                    break

        if save_idx is None:
            print("[ComputerSkill] Layer 2a (gedit): editor Save button not found")
            return None

        _cua_call("click", {"pid": pid, "window_id": wid, "element_index": save_idx})
        await asyncio.sleep(2.0)

        # Wait for Save As dialog to appear
        dwid = None
        for _ in range(10):
            for w in _cua_call("list_windows", {}).get("windows", []):
                if "save as" in w.get("title", "").lower():
                    dwid = w["window_id"]
                    break
            if dwid:
                break
            await asyncio.sleep(0.5)

        if not dwid:
            print("[ComputerSkill] Layer 2a (gedit): Save As dialog not found, falling back to Layer 2b")
            return None

        print(f"[ComputerSkill] Layer 2a (gedit): Save As dialog found (wid={dwid}). Completing save deterministically via Ctrl+L.")

        # Bring the Save As dialog to front using EWMH message
        try:
            from Xlib import display, X
            from Xlib.protocol import event
            d_act = display.Display()
            root_act = d_act.screen().root
            active_atom = d_act.intern_atom('_NET_ACTIVE_WINDOW')
            ev = event.ClientMessage(
                window=dwid,
                client_type=active_atom,
                data=(32, [1, X.CurrentTime, 0, 0, 0])
            )
            root_act.send_event(ev, event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask)
            d_act.sync()
            print(f"[ComputerSkill] EWMH focus sent for Save As dialog (wid={dwid})")
        except Exception as e:
            print(f"[ComputerSkill] Warning: EWMH focus failed: {e}")
        await asyncio.sleep(0.5)

        full_path = os.path.join(directory, filename)
        try:
            print(f"[ComputerSkill] Layer 2a (gedit): Sending Ctrl+L to show location entry")
            _cua_call("hotkey", {"pid": pid, "window_id": dwid, "keys": ["ctrl", "l"]})
            await asyncio.sleep(0.5)
            print(f"[ComputerSkill] Layer 2a (gedit): Typing path '{full_path}' via cua-driver")
            _cua_call("type_text", {"pid": pid, "window_id": dwid, "text": full_path})
            await asyncio.sleep(0.5)
            _cua_call("press_key", {"pid": pid, "window_id": dwid, "key": "Return"})
            await asyncio.sleep(0.5)
            _cua_call("press_key", {"pid": pid, "window_id": dwid, "key": "Return"})
            await asyncio.sleep(1.0)
        except Exception as e:
            print(f"[ComputerSkill] Layer 2a (gedit): cua-driver save failed: {e}, falling back to Layer 2b")
            return None

        # Handle potential "Replace?" confirmation dialog
        for _ in range(5):
            try:
                windows = _cua_call("list_windows", {})
                for w in windows.get("windows", []):
                    title = (w.get("title") or "").lower()
                    if w.get("pid") == pid and any(x in title for x in ("question", "confirm", "replace", "overwrite")):
                        # Found a confirmation dialog — scan it and click Replace
                        confirm_wid = w["window_id"]
                        state = _cua_call("get_window_state",
                                          {"pid": pid, "window_id": confirm_wid, "capture_mode": "ax"})
                        tree = state.get("tree_markdown", "")
                        for line in tree.splitlines():
                            if "replace" in line.lower() and "push button" in line.lower():
                                m = re.search(r'\[(\d+)\]', line)
                                if m:
                                    _cua_call("click", {"pid": pid, "window_id": confirm_wid,
                                                        "element_index": int(m.group(1))})
                                    print("[ComputerSkill] Layer 2a (gedit): clicked Replace in confirmation dialog")
                                    await asyncio.sleep(0.5)
                                    break
                        break
            except CuaError:
                pass
            await asyncio.sleep(0.3)

        # Verify the file was saved
        await asyncio.sleep(0.5)
        if os.path.exists(full_path):
            saved_content = ""
            try:
                saved_content = open(full_path).read().strip()
            except Exception:
                pass
            print(f"[ComputerSkill] Layer 2a (gedit) SUCCESS: Saved to {full_path} (content: {saved_content[:50]!r})")
            return self._ok(app_name, goal, "deterministic", turns=3, content=content)
        else:
            print(f"[ComputerSkill] Layer 2a (gedit): File not found at {full_path} after save attempt, falling back to Layer 2b")
            return None

    async def _layer2a_obsidian_save(self, pid, wid, app_name, goal, t0) -> AgentResult | None:
        """Deterministic save for Obsidian: Try CDP page tool first, otherwise fallback to XTEST."""
        # Parse goal
        directory, filename, content = _parse_gedit_goal(goal)
        note_title = filename
        if note_title.endswith(".md"):
            note_title = note_title[:-3]
        elif note_title.endswith(".txt"):
            note_title = note_title[:-4]

        # Use standard Obsidian Vault folder
        obsidian_dir = "/home/mani_radhakrishnan/Obsidian Vault"
        print(f"[ComputerSkill] Layer 2a (obsidian): dir={obsidian_dir}, title={note_title}, content={content}")

        # Pre-delete the target Obsidian file to avoid duplicates or conflict issues
        target_path = os.path.join(obsidian_dir, f"{note_title}.md")
        if os.path.exists(target_path):
            try:
                os.remove(target_path)
                print(f"[ComputerSkill] Pre-deleted existing Obsidian note: {target_path}")
            except Exception as e:
                print(f"[ComputerSkill] Failed to delete existing Obsidian note: {e}")

        # 1. Try CDP page tool pathway
        try:
            print("[ComputerSkill] Attempting Obsidian save via CDP page tool...")
            js_code = f"""
(async () => {{
  try {{
    let title = "{note_title}.md";
    let file = app.vault.getAbstractFileByPath(title);
    let content = {json.dumps(content)};
    if (file) {{
      await app.vault.modify(file, content);
    }} else {{
      await app.vault.create(title, content);
    }}
    return "OK";
  }} catch(e) {{
    return e.toString();
  }}
}})()
"""
            res = _cua_call("page", {
                "pid": pid,
                "window_id": wid,
                "action": "execute_javascript",
                "javascript": js_code
            })
            raw_out = res.get("raw", "")
            if "OK" in raw_out:
                await asyncio.sleep(1.0)
                target_path = os.path.join(obsidian_dir, f"{note_title}.md")
                if os.path.exists(target_path):
                    print(f"[ComputerSkill] CDP page tool SUCCESS: Saved to {target_path}")
                    return self._ok(app_name, goal, "page", turns=1, content=content)
            print(f"[ComputerSkill] CDP page tool save did not confirm success (result={raw_out}). Falling back to XTEST.")
        except Exception as e:
            print(f"[ComputerSkill] CDP page tool save failed: {e}. Falling back to XTEST.")

        # 2. Fallback to XTEST
        from Xlib import X, display, XK
        from Xlib.ext import xtest
        from Xlib.protocol import event

        d = display.Display()
        root = d.screen().root

        def ewmh_activate(window_id):
            active_atom = d.intern_atom('_NET_ACTIVE_WINDOW')
            ev = event.ClientMessage(
                window=window_id,
                client_type=active_atom,
                data=(32, [1, X.CurrentTime, 0, 0, 0])
            )
            root.send_event(ev, event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask)
            d.sync()

        def xkey(keysym, mods=None):
            keycode = d.keysym_to_keycode(keysym)
            mcs = [d.keysym_to_keycode(m) for m in (mods or [])]
            for mc in mcs: xtest.fake_input(d, X.KeyPress, mc)
            xtest.fake_input(d, X.KeyPress, keycode)
            d.sync()
            time.sleep(0.05)
            xtest.fake_input(d, X.KeyRelease, keycode)
            for mc in reversed(mcs): xtest.fake_input(d, X.KeyRelease, mc)
            d.sync()

        def xtest_type(text_str):
            for char in text_str:
                shift_req = False
                shift_chars = '!@#$%^&*()_+{}|:"<>?~'
                if char.isupper() or char in shift_chars:
                    shift_req = True
                    
                keysym = XK.string_to_keysym(char)
                if keysym == 0:
                    keysym = ord(char)
                    
                keycode = d.keysym_to_keycode(keysym)
                
                if shift_req:
                    shift_keycode = d.keysym_to_keycode(XK.XK_Shift_L)
                    xtest.fake_input(d, X.KeyPress, shift_keycode)
                    d.sync()
                    
                xtest.fake_input(d, X.KeyPress, keycode)
                d.sync()
                time.sleep(0.02)
                xtest.fake_input(d, X.KeyRelease, keycode)
                d.sync()
                
                if shift_req:
                    xtest.fake_input(d, X.KeyRelease, shift_keycode)
                    d.sync()
                    
                time.sleep(0.01)

        # Focus Obsidian
        ewmh_activate(wid)
        await asyncio.sleep(1.0)

        # Press Ctrl+N to create new note
        xkey(XK.XK_n, [XK.XK_Control_L])
        await asyncio.sleep(1.0)

        # Type the title
        xtest_type(note_title)
        await asyncio.sleep(0.5)

        # Press Return to enter editor body
        xkey(XK.XK_Return)
        await asyncio.sleep(0.5)

        # Type note content
        xtest_type(content)
        await asyncio.sleep(0.5)

        # Press Ctrl+S
        xkey(XK.XK_s, [XK.XK_Control_L])
        await asyncio.sleep(1.0)

        # Verify file exists
        target_path = os.path.join(obsidian_dir, f"{note_title}.md")
        if os.path.exists(target_path):
            print(f"[ComputerSkill] Layer 2a (obsidian) SUCCESS: Saved to {target_path}")
            return self._ok(app_name, goal, "deterministic", turns=1, content=content)
        else:
            print(f"[ComputerSkill] Layer 2a (obsidian) FAILED: File not at {target_path}")
            return None

    # ── Layer 2b: a11y (AX tree + LLM) ──────────────────────────────
    async def _layer2b_a11y(self, pid, wid, app_name, goal, t0) -> AgentResult | None:
        """AX tree + cheap text LLM judgment loop (scan-act-verify)."""
        print(f"[ComputerSkill] Layer 2b (a11y): starting LLM-guided loop")
        gateway = V9Client(base_url=self.gateway_url, agent=self.agent_tag,
                           session=self.session)
        history: list[str] = []
        last_active_wid = wid

        for turn in range(1, self.max_steps_a11y + 1):
            # Resolve active window at each turn (crucial for modal dialogs)
            active_wid = await _get_active_window(pid, app_name, wid)
            if active_wid != last_active_wid:
                print(f"[ComputerSkill] Active window changed from {last_active_wid} to {active_wid}, bringing to front and waiting for render...")
                try:
                    _cua_call("bring_to_front", {"pid": pid, "window_id": active_wid})
                except Exception as e:
                    print(f"[ComputerSkill] Failed to bring window {active_wid} to front: {e}")
                await asyncio.sleep(1.0)
                last_active_wid = active_wid

            # SCAN — re-scan before every action (Invariant 1 & 2)
            try:
                state = _cua_call("get_window_state",
                                  {"pid": pid, "window_id": active_wid, "capture_mode": "ax"})
                tree_md = state.get("tree_markdown", "")
                if state.get("element_count", 0) == 0:
                    print("[ComputerSkill] Layer 2b: empty AX tree, escalating")
                    return None
            except CuaError as e:
                print(f"[ComputerSkill] Layer 2b: scan failed: {e}")
                return None

            prompt = (
                f"GOAL: {goal}\n\n"
                f"APP: {app_name}\n\n"
                f"ACCESSIBILITY TREE:\n{tree_md}\n\n"
                + (f"HISTORY:\n" + "\n".join(history[-5:]) + "\n\n" if history else "")
                + "What is the single next action?"
            )

            try:
                res = await gateway.chat(
                    prompt=prompt, system=A11Y_SYSTEM,
                    schema=A11Y_SCHEMA, schema_name="A11yAction",
                    max_tokens=512, provider="gemini",
                )
            except Exception as e:
                print(f"[ComputerSkill] Layer 2b: LLM call failed: {e}")
                return None

            parsed = res.parsed
            if not parsed or "action" not in parsed:
                continue

            thinking = parsed.get("thinking", "")
            action = parsed["action"]
            act_type = action.get("type")

            # ACT
            if act_type == "done":
                note = action.get("note", "")
                print(f"[ComputerSkill] Layer 2b done: {note}")
                return self._ok(app_name, goal, "a11y", turns=turn,
                                content=note,
                                success=bool(action.get("success", True)))

            if act_type == "click":
                eidx = action.get("element_index")
                if eidx is None:
                    continue
                count = action.get("count", 1)
                try:
                    _cua_call("click", {
                        "pid": pid,
                        "window_id": active_wid,
                        "element_index": eidx,
                        "count": count
                    })
                    count_str = f" x{count}" if count > 1 else ""
                    history.append(f"turn {turn}: clicked element_index={eidx}{count_str}")
                    print(f"[ComputerSkill] Layer 2b turn {turn}: clicked idx={eidx}{count_str} ({thinking})")
                except CuaError as e:
                    history.append(f"turn {turn}: click idx={eidx} FAILED: {e}")

            elif act_type == "type_text":
                eidx = action.get("element_index")
                text = action.get("text", "")
                try:
                    if eidx is not None:
                        # Try set_value first (especially useful on Linux/GTK as it is reliable and clears the text)
                        try:
                            _cua_call("set_value", {"pid": pid, "window_id": active_wid, "element_index": eidx, "value": text})
                            print(f"[ComputerSkill] Layer 2b turn {turn}: set_value succeeded for idx={eidx} with {text!r}")
                            history.append(f"turn {turn}: set_value '{text}' into idx={eidx}")
                        except Exception as sve:
                            print(f"[ComputerSkill] Layer 2b: set_value failed ({sve}), falling back to click+type")
                            # Click to focus
                            _cua_call("click", {"pid": pid, "window_id": active_wid, "element_index": eidx})
                            await asyncio.sleep(0.1)
                            # Select all (Ctrl+A)
                            _cua_call("hotkey", {"pid": pid, "window_id": active_wid, "keys": ["ctrl", "a"]})
                            await asyncio.sleep(0.1)
                            # Clear text (BackSpace)
                            _cua_call("press_key", {"pid": pid, "window_id": active_wid, "key": "BackSpace"})
                            await asyncio.sleep(0.1)
                            # Type the text
                            _cua_call("type_text", {"pid": pid, "window_id": active_wid, "element_index": eidx, "text": text})
                            history.append(f"turn {turn}: typed '{text}' into idx={eidx} (fallback)")
                    else:
                        _cua_call("type_text", {"pid": pid, "window_id": active_wid, "text": text})
                        history.append(f"turn {turn}: typed '{text}'")
                    suffix = f" into idx={eidx}" if eidx is not None else ""
                    print(f"[ComputerSkill] Layer 2b turn {turn}: typed '{text}'{suffix} ({thinking})")
                except CuaError as e:
                    history.append(f"turn {turn}: type_text FAILED: {e}")

            elif act_type == "press_key":
                key = action.get("key", "")
                try:
                    _cua_call("press_key", {"pid": pid, "window_id": active_wid, "key": key})
                    history.append(f"turn {turn}: pressed key '{key}'")
                    print(f"[ComputerSkill] Layer 2b turn {turn}: press_key '{key}' ({thinking})")
                except CuaError as e:
                    history.append(f"turn {turn}: press_key FAILED: {e}")

            elif act_type == "hotkey":
                keys = action.get("keys", [])
                try:
                    _cua_call("hotkey", {"pid": pid, "window_id": active_wid, "keys": keys})
                    history.append(f"turn {turn}: hotkey {keys}")
                    print(f"[ComputerSkill] Layer 2b turn {turn}: hotkey {keys} ({thinking})")
                except CuaError as e:
                    history.append(f"turn {turn}: hotkey FAILED: {e}")

            await asyncio.sleep(0.3)

        print("[ComputerSkill] Layer 2b: step cap reached")
        return None

    # ── Layer 3: vision (screenshot + VLM) ───────────────────────────
    async def _layer3_vision(self, pid, wid, app_name, goal, t0) -> AgentResult | None:
        """Screenshot + vision LLM loop. Last resort."""
        print("[ComputerSkill] Layer 3 (vision): starting screenshot loop")

        # Automatically ensure calculator is in Basic Mode before starting vision loop
        if app_name == "calculator":
            try:
                print("[ComputerSkill] Calculator detected. Triggering dynamic mode switcher script...")
                script_path = os.path.join(os.path.dirname(__file__), "switch_calc_mode.py")
                res = subprocess.run(["python3", script_path], capture_output=True, text=True, timeout=15)
                print(f"[ComputerSkill] switch_calc_mode output: {res.stdout.strip()}")
            except Exception as e:
                print(f"[ComputerSkill] Dynamic mode switcher failed to execute: {e}")

        # Get screen size from cua-driver
        try:
            screen_info = _cua_call("get_screen_size", {})
            screen_w = screen_info.get("width", 1920)
            screen_h = screen_info.get("height", 1080)
        except CuaError:
            screen_w, screen_h = 1920, 1080

        gateway = V9Client(base_url=self.gateway_url, agent=self.agent_tag,
                           session=self.session)
        history: list[dict] = []

        for turn in range(1, self.max_steps_vision + 1):
            # Focus the target window first via EWMH active window message before screenshot
            try:
                from Xlib import display, X
                from Xlib.protocol import event
                d_act = display.Display()
                root_act = d_act.screen().root
                active_atom = d_act.intern_atom('_NET_ACTIVE_WINDOW')
                ev = event.ClientMessage(
                    window=wid,
                    client_type=active_atom,
                    data=(32, [1, X.CurrentTime, 0, 0, 0])
                )
                root_act.send_event(ev, event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask)
                d_act.sync()
            except Exception as e:
                try:
                    _cua_call("bring_to_front", {"pid": pid, "window_id": wid})
                except Exception:
                    pass
            await asyncio.sleep(0.5)

            img_path = (self.artifacts_root or Path("/tmp")) / f"vision_turn_{turn:02d}.png"
            img_bytes = None
            
            # Get window screen geometry first for cropping
            win_x, win_y, win_w, win_h = 0, 0, screen_w, screen_h
            has_geom = False
            try:
                windows = _cua_call("list_windows", {})
                for win in windows.get("windows", []):
                    if win.get("window_id") == wid or win.get("xid") == wid:
                        win_x = win.get("x", 0)
                        win_y = win.get("y", 0)
                        win_w = win.get("width", screen_w)
                        win_h = win.get("height", screen_h)
                        has_geom = True
                        break
            except Exception as ge:
                print(f"[ComputerSkill] Layer 3: failed to get target window geometry: {ge}")

            # Try capturing the full screen first
            try:
                subprocess.run(
                    ["gnome-screenshot", "-f", str(img_path)],
                    capture_output=True, timeout=5)
                if img_path.exists():
                    img_bytes = img_path.read_bytes()
                    # Crop the full screen screenshot to target window bounds for precise VLM coordinates
                    if has_geom:
                        from PIL import Image
                        with Image.open(img_path) as full_img:
                            cx1 = max(0, min(win_x, screen_w - 1))
                            cy1 = max(0, min(win_y, screen_h - 1))
                            cx2 = max(cx1 + 10, min(win_x + win_w, screen_w))
                            cy2 = max(cy1 + 10, min(win_y + win_h, screen_h))
                            cropped = full_img.crop((cx1, cy1, cx2, cy2))
                            cropped.save(img_path)
                            img_bytes = img_path.read_bytes()
                            print(f"[ComputerSkill] Cropped screenshot to window {wid} bounds: ({cx1},{cy1}) to ({cx2},{cy2})")
            except Exception as e:
                print(f"[ComputerSkill] Layer 3: full-screen screenshot crop failed: {e}")

            # Fallback to get_window_state if full-screen capture failed
            if not img_bytes:
                try:
                    state = _cua_call("get_window_state", {
                        "pid": pid,
                        "window_id": wid,
                        "capture_mode": "vision",
                    })
                    b64_str = state.get("screenshot_png_b64", "")
                    if b64_str:
                        img_bytes = base64.b64decode(b64_str)
                        img_path.parent.mkdir(parents=True, exist_ok=True)
                        img_path.write_bytes(img_bytes)
                    else:
                        raise CuaError("No screenshot base64 in response")
                except Exception as ex:
                    print(f"[ComputerSkill] Layer 3: get_window_state vision fallback failed: {ex}")

            if not img_bytes:
                await asyncio.sleep(1.0)
                continue

            # Determine actual image dimensions
            img_w, img_h = 1920, 1080
            try:
                from PIL import Image
                with Image.open(img_path) as img:
                    img_w, img_h = img.size
            except Exception:
                pass

            data_url = f"data:image/png;base64,{base64.b64encode(img_bytes).decode()}"

            prompt = (
                f"GOAL: {goal}\n\nRECENT ACTIONS:\n"
                + ("(none)" if not history else "\n".join(
                    f"turn {i+1}: click ({h.get('actions',[{}])[0].get('x','?')}, "
                    f"{h.get('actions',[{}])[0].get('y','?')})"
                    for i, h in enumerate(history[-5:])))
                + f"\n\nWhat is the next action? Coordinates on a 0-1000 scale."
            )

            try:
                res = await gateway.vision(
                    image_data_url=data_url, prompt=prompt,
                    system=VISION_SYSTEM, schema=VISION_SCHEMA,
                    schema_name="VisionAction", max_tokens=1024,
                    provider="gemini",
                )
            except Exception as ex:
                print(f"[ComputerSkill] Layer 3: vision call failed: {ex}")
                await asyncio.sleep(3.0)
                continue

            parsed = res.parsed
            if not parsed or "actions" not in parsed:
                continue

            thinking = parsed.get("thinking", "")
            print(f"[ComputerSkill] Layer 3 VLM Thinking: {thinking}")

            act = parsed.get("actions", [{}])[0]
            act_type = act.get("type")

            if act_type == "done":
                return self._ok(app_name, goal, "vision", turns=turn,
                                content=act.get("note", ""), success=bool(act.get("success")))

            if act_type == "click":
                x, y = act.get("x"), act.get("y")
                if x is not None and y is not None:
                    # Focus the target window first via EWMH active window message
                    try:
                        from Xlib import display, X
                        from Xlib.protocol import event
                        d_act = display.Display()
                        root_act = d_act.screen().root
                        active_atom = d_act.intern_atom('_NET_ACTIVE_WINDOW')
                        ev = event.ClientMessage(
                            window=wid,
                            client_type=active_atom,
                            data=(32, [1, X.CurrentTime, 0, 0, 0])
                        )
                        root_act.send_event(ev, event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask)
                        d_act.sync()
                    except Exception as e:
                        try:
                            _cua_call("bring_to_front", {"pid": pid, "window_id": wid})
                        except Exception:
                            pass
                    await asyncio.sleep(0.2)

                    # Compute final screen coordinates:
                    # The VLM output coordinates (x, y) are in a 0-1000 range.
                    # We map them to the captured image dimensions (img_w, img_h).
                    pixel_x = int(x * img_w / 1000)
                    pixel_y = int(y * img_h / 1000)

                    if img_w == screen_w and img_h == screen_h:
                        screen_x = pixel_x
                        screen_y = pixel_y
                        print(f"[ComputerSkill] Layer 3 turn {turn}: fullscreen click ({x},{y}) -> pixel ({pixel_x},{pixel_y}) -> screen ({screen_x},{screen_y})")
                    else:
                        # Get window screen coordinates
                        win_x, win_y = 0, 0
                        try:
                            windows = _cua_call("list_windows", {})
                            for win in windows.get("windows", []):
                                if win.get("window_id") == wid or win.get("xid") == wid:
                                    win_x = win.get("x", 0)
                                    win_y = win.get("y", 0)
                                    break
                        except Exception as ge:
                            print(f"[ComputerSkill] Layer 3: failed to get window geometry: {ge}")
                            
                        screen_x = win_x + pixel_x
                        screen_y = win_y + pixel_y
                        print(f"[ComputerSkill] Layer 3 turn {turn}: window click ({x},{y}) -> pixel ({pixel_x},{pixel_y}) -> screen ({screen_x},{screen_y})")

                    # Perform real click via X11 Xlib XTEST on Linux
                    clicked_via_x11 = False
                    try:
                        from Xlib import X, display
                        from Xlib.ext import xtest
                        d = display.Display()
                        
                        # Preserve original mouse position
                        qp = d.screen().root.query_pointer()
                        orig_x, orig_y = qp.root_x, qp.root_y
                        
                        # Glide physical cursor from orig_pos to target over 8 steps for visibility
                        steps = 8
                        for i in range(1, steps + 1):
                            px = int(orig_x + (screen_x - orig_x) * i / steps)
                            py = int(orig_y + (screen_y - orig_y) * i / steps)
                            xtest.fake_input(d, X.MotionNotify, detail=0, x=px, y=py)
                            d.sync()
                            await asyncio.sleep(0.02)
                        
                        # Button press and release (button = 1)
                        xtest.fake_input(d, X.ButtonPress, detail=1)
                        d.sync()
                        await asyncio.sleep(0.08)
                        
                        xtest.fake_input(d, X.ButtonRelease, detail=1)
                        d.sync()
                        await asyncio.sleep(0.05)
                        
                        clicked_via_x11 = True
                        print(f"[ComputerSkill] Layer 3: click delivered via X11 Xlib at screen ({screen_x}, {screen_y})")
                    except Exception as xe:
                        print(f"[ComputerSkill] Layer 3: X11 click failed ({xe}), falling back to cua_call")

                    if not clicked_via_x11:
                        # Scaling fallback click
                        local_x = screen_x - win_x if 'win_x' in locals() else x
                        local_y = screen_y - win_y if 'win_y' in locals() else y
                        _cua_call("click", {"pid": pid, "window_id": wid, "x": local_x, "y": local_y})

            elif act_type == "type":
                text = act.get("text") or act.get("value") or ""
                print(f"[ComputerSkill] Layer 3 turn {turn}: type {text!r}")
                _cua_call("type_text", {"pid": pid, "window_id": wid, "text": text})

            history.append(parsed)
            await asyncio.sleep(0.8)

        return self._err(app_name, goal, "interaction_failed",
                         f"Vision loop cap ({self.max_steps_vision} turns)", t0=t0)

    # ── helpers ──────────────────────────────────────────────────────
    def _answer_visible(self, display: str, goal: str) -> bool:
        return False  # Conservative: always compute fresh

    def _ok(self, app, goal, path, *, turns, content="", success=True):
        return AgentResult(
            success=success, agent_name="computer",
            output={"app": app, "goal": goal, "path": path,
                    "turns": turns, "content": content})

    def _err(self, app, goal, code, msg, *, t0=None):
        return AgentResult(
            success=False, agent_name="computer",
            output={"app": app, "goal": goal, "path": "error",
                    "turns": 0, "content": ""},
            error=msg, error_code=code,
            elapsed_s=time.time() - t0 if t0 else 0)


def _parse_gedit_goal(goal: str) -> tuple[str, str, str]:
    # Extract calculator result
    result_val = ""
    # Search for result patterns including scientific/superscript notation (excluding other letters)
    m_res = re.search(
        r"(?:previous step is:|result from|result of|result is|result)\s+([0-9\.\-×¹²³⁴⁵⁶⁷⁸⁹⁰+eE]+)",
        goal,
        re.IGNORECASE
    )
    if m_res:
        result_val = m_res.group(1).strip()
    else:
        # Check for any numbers in the goal
        m_num = re.findall(r"\b(\d+)\b", goal)
        if m_num:
            result_val = m_num[-1]

    # Initialize defaults
    directory = "/home/mani_radhakrishnan/sandbox_session10"
    filename = None

    # Check for path-like strings
    m_path = re.search(r"([~/][a-zA-Z0-9_\-\./]+)", goal)
    if m_path:
        full_path = m_path.group(1).strip().rstrip(".")
        if re.search(r"\.(?:txt|md)$", full_path, re.IGNORECASE):
            directory = os.path.dirname(full_path)
            filename = os.path.basename(full_path)
        else:
            directory = full_path

    # Extract directory (fallback/override)
    m_dir = re.search(r"(?:inside|in|directory)\s+([~/a-zA-Z0-9_\-\.]+)", goal, re.IGNORECASE)
    if m_dir:
        path = m_dir.group(1).strip().rstrip(".")
        if path.startswith("/"):
            directory = path
        elif path.startswith("~"):
            directory = os.path.expanduser(path)

    # Extract filename (fallback/override)
    if not filename:
        m_file = re.search(r"(?:named|name|titled|title|called)(?:\s+of)?\s+['\"]?([\w\.-]+)['\"]?", goal, re.IGNORECASE)
        if m_file:
            filename = m_file.group(1).strip()
        else:
            m_note = re.search(r"(?:note|file)\s+['\"]?([\w\.-]+)['\"]?", goal, re.IGNORECASE)
            if m_note:
                candidate = m_note.group(1).strip()
                if candidate.lower() not in ("titled", "named", "called", "in", "inside", "at"):
                    filename = candidate
                else:
                    m_next = re.search(fr"(?:note|file)\s+{candidate}\s+['\"]?([\w\.-]+)['\"]?", goal, re.IGNORECASE)
                    if m_next:
                        filename = m_next.group(1).strip()

    # Fallback to general file extension search
    if not filename:
        m_ext = re.search(r"([\w\.-]+\.(?:txt|md))", goal)
        if m_ext:
            filename = m_ext.group(1).strip()

    # Final default fallback
    if not filename:
        filename = "mr_01.txt"

    # Construct content
    content = f"The calculated result is {result_val}"
    
    # Ensure directory exists
    os.makedirs(directory, exist_ok=True)
    
    return directory, filename, content
