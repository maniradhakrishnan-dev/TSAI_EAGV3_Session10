import json
import subprocess
import time

def _cua_call(action: str, args: dict = None) -> dict:
    cmd = ["/home/mani_radhakrishnan/.local/bin/cua-driver", "call", action, json.dumps(args or {})]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    out = res.stdout.strip()
    if out.startswith(("{", "[")):
        return json.loads(out)
    return {"raw": out}

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
    print(f"Calculator pid={pid}, wid={wid}")

    # Click Mode selection toggle button (index 4)
    print("Clicking Mode selection toggle button (index 4)...")
    res1 = _cua_call("click", {"pid": pid, "window_id": wid, "element_index": 4})
    print("Result 1:", res1)
    time.sleep(1.0)

    # Click Basic Mode radio button (index 345)
    print("Clicking Basic Mode radio button (index 345)...")
    res2 = _cua_call("click", {"pid": pid, "window_id": wid, "element_index": 345})
    print("Result 2:", res2)
    time.sleep(1.0)

    # Verify: print the first 20 lines of the AX tree
    state = _cua_call("get_window_state", {
        "pid": pid,
        "window_id": wid,
        "capture_mode": "ax"
    })
    print("\n--- Top of new AX tree ---")
    tree = state.get("tree_markdown", "")
    for line in tree.splitlines()[:20]:
        print(line)

if __name__ == "__main__":
    main()
