import json
import subprocess
import time

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
    print(f"Focusing Calculator (pid={pid}, wid={wid})...")
    try:
        _cua_call("bring_to_front", {"pid": pid, "window_id": wid})
    except Exception as e:
        print(f"bring_to_front failed: {e}")
    time.sleep(0.5)

    # Click Mode selection toggle button
    print("Clicking Mode selection button (idx=4)...")
    try:
        _cua_call("click", {"pid": pid, "window_id": wid, "element_index": 4})
    except Exception as e:
        print(f"Clicking mode selection failed: {e}")
    time.sleep(0.5)

    # Click Basic Mode radio button
    print("Clicking Basic Mode (idx=345)...")
    try:
        _cua_call("click", {"pid": pid, "window_id": wid, "element_index": 345})
    except Exception as e:
        print(f"Clicking basic mode failed: {e}")
    time.sleep(0.5)

    # Dump the new AX tree
    state = _cua_call("get_window_state", {
        "pid": pid,
        "window_id": wid,
        "capture_mode": "ax"
    })
    with open("scratch/calc_ax_after_click_mode.txt", "w") as f:
        f.write(state.get("tree_markdown", ""))
    print("New AX tree saved to scratch/calc_ax_after_click_mode.txt")

if __name__ == "__main__":
    main()
