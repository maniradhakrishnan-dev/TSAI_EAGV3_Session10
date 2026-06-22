import json
import subprocess
import time
from Xlib import X, display
from Xlib.ext import xtest

def _cua_call(action: str, args: dict = None) -> dict:
    cmd = ["/home/mani_radhakrishnan/.local/bin/cua-driver", "call", action, json.dumps(args or {})]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    out = res.stdout.strip()
    if out.startswith(("{", "[")):
        return json.loads(out)
    return {"raw": out}

def xclick(screen_x, screen_y):
    d = display.Display()
    xtest.fake_input(d, X.MotionNotify, detail=0, x=screen_x, y=screen_y)
    d.sync()
    time.sleep(0.2)
    xtest.fake_input(d, X.ButtonPress, detail=1)
    d.sync()
    time.sleep(0.1)
    xtest.fake_input(d, X.ButtonRelease, detail=1)
    d.sync()
    time.sleep(0.2)

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

    # Focus
    d = display.Display()
    from Xlib.protocol import event
    root = d.screen().root
    active_atom = d.intern_atom('_NET_ACTIVE_WINDOW')
    ev = event.ClientMessage(
        window=wid,
        client_type=active_atom,
        data=(32, [1, X.CurrentTime, 0, 0, 0])
    )
    root.send_event(ev, event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask)
    d.sync()
    time.sleep(0.5)

    # Click Mode selection button via physical X11 click at (1071, 119)
    print("Clicking Mode selection button at (1071, 119)...")
    xclick(1071, 119)
    time.sleep(1.5)

    # Fetch window state to get "Basic Mode" coordinates
    state2 = _cua_call("get_window_state", {
        "pid": pid,
        "window_id": wid,
        "capture_mode": "ax"
    })
    
    basic_btn = None
    for el in state2.get("elements", []):
        if el.get("name") == "Basic Mode":
            basic_btn = el
            break

    if not basic_btn:
        print("Basic Mode button not found in elements! Printing available names:")
        names = [el.get("name") for el in state2.get("elements", []) if el.get("name")]
        print(names)
        return

    bx = basic_btn.get("x", 0)
    by = basic_btn.get("y", 0)
    bw = basic_btn.get("width", 0)
    bh = basic_btn.get("height", 0)
    bcx = bx + bw // 2
    bcy = by + bh // 2

    print(f"Clicking Basic Mode at ({bcx}, {bcy})...")
    xclick(bcx, bcy)
    time.sleep(1.5)

    # Dump tree to verify
    state3 = _cua_call("get_window_state", {
        "pid": pid,
        "window_id": wid,
        "capture_mode": "ax"
    })
    
    with open("scratch/calc_ax_physical_switch.txt", "w") as f:
        f.write(state3.get("tree_markdown", ""))
    print("AX tree dumped to scratch/calc_ax_physical_switch.txt")

if __name__ == "__main__":
    main()
