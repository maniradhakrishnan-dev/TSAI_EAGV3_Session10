import asyncio
import json
import sys
import subprocess
import os
from pathlib import Path

# Add S9SharedCode/code/ to system path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from computer.skill import _cua_call, _ensure_daemon

async def main():
    _ensure_daemon()
    
    # Close any existing gedit
    subprocess.run(["killall", "gedit"], capture_output=True)
    await asyncio.sleep(0.5)
    
    # Launch gedit
    env = dict(os.environ)
    env["DISPLAY"] = os.environ.get("DISPLAY", ":0")
    proc = subprocess.Popen(["gedit"], env=env)
    pid = proc.pid
    print(f"Launched gedit with PID: {pid}")
    
    # Wait for window
    wid = None
    for attempt in range(10):
        try:
            windows = _cua_call("list_windows", {})
            for w in windows.get("windows", []):
                if w.get("pid") == pid:
                    wid = w["window_id"]
                    break
            if wid:
                break
        except Exception:
            pass
        await asyncio.sleep(0.5)
        
    if not wid:
        print("Could not find gedit window ID")
        return
        
    print(f"Found gedit window ID: {wid}")
    await asyncio.sleep(1.0)
    
    # Scan tree to find Save button
    state = _cua_call("get_window_state", {"pid": pid, "window_id": wid, "capture_mode": "ax"})
    tree_md = state.get("tree_markdown", "")
    print(f"Initial element count: {state.get('element_count', 0)}")
    
    # Find Save button by label
    # In gedit AX tree, 'Save' is usually a button
    import re
    # Match Save button
    m = re.search(r'-\s*\[(\d+)\]\s+push button\s+"Save"', tree_md)
    if not m:
        # Fallback to any button named Save
        m = re.search(r'-\s*\[(\d+)\]\s+.*"Save"', tree_md)
        
    if not m:
        print("Could not find Save button in initial AX tree")
        return
        
    save_idx = int(m.group(1))
    print(f"Clicking Save button (element_index={save_idx})")
    _cua_call("click", {"pid": pid, "window_id": wid, "element_index": save_idx})
    
    # Wait for Save As dialog to open
    await asyncio.sleep(1.5)
    
    # Capture state of Save As dialog
    state_dialog = _cua_call("get_window_state", {"pid": pid, "window_id": wid, "capture_mode": "ax"})
    
    output_path = Path(__file__).resolve().parent / "save_dialog_state.json"
    with open(output_path, "w") as f:
        json.dump(state_dialog, f, indent=2)
        
    print(f"Dumped Save As dialog state to: {output_path}")
    print(f"Elements in dialog: {state_dialog.get('element_count', 0)}")
    
    # Clean up gedit
    subprocess.run(["killall", "gedit"], capture_output=True)

if __name__ == "__main__":
    asyncio.run(main())
