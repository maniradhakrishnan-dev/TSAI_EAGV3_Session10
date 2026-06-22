import json
import subprocess

def _cua_call(action: str, args: dict = None) -> dict:
    cmd = ["/home/mani_radhakrishnan/.local/bin/cua-driver", "call", action, json.dumps(args or {})]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(res.stdout)

def main():
    # Find Calculator window
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
    print(f"Calculator: pid={pid}, window_id={wid}, x={calc_win['x']}, y={calc_win['y']}, w={calc_win['width']}, h={calc_win['height']}")

    state = _cua_call("get_window_state", {
        "pid": pid,
        "window_id": wid,
        "capture_mode": "ax"
    })
    
    print("\n--- AX Elements with Labels ---")
    tree_md = state.get("tree_markdown", "")
    for line in tree_md.splitlines():
        if any(lbl in line for lbl in ["'1'", "'2'", "'3'", "'4'", "'5'", "'6'", "'7'", "'8'", "'9'", "'0'"]):
            print(line)

if __name__ == "__main__":
    main()
