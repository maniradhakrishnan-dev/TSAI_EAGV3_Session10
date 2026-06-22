import json
import subprocess
import shutil
import os

def _cua_call(action: str, args: dict = None) -> dict:
    cmd = ["/home/mani_radhakrishnan/.local/bin/cua-driver", "call", action, json.dumps(args or {})]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(res.stdout)

def main():
    wins = _cua_call("list_windows", {})
    calc_win = None
    for win in wins.get("windows", []):
        if "calculator" in win.get("title", "").lower():
            calc_win = win
            break
    
    if not calc_win:
        print("Calculator window not found!")
        return

    pid = calc_win["pid"]
    wid = calc_win["window_id"]
    
    state = _cua_call("get_window_state", {
        "pid": pid,
        "window_id": wid,
        "capture_mode": "vision"
    })
    
    src = state.get("screenshot_path")
    if src and os.path.exists(src):
        dst = "/home/mani_radhakrishnan/.gemini/antigravity/brain/1127d650-97f7-4389-a0d0-0c4991946c47/calc_screenshot.png"
        shutil.copy(src, dst)
        print(f"Screenshot copied to {dst}")
    else:
        print("No screenshot path found in state:", state)

if __name__ == "__main__":
    main()
