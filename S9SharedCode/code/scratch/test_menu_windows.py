import json
import subprocess
import time
from Xlib import X, display
from Xlib.ext import xtest

def _cua_call(action: str, args: dict = None) -> dict:
    cmd = ["/home/mani_radhakrishnan/.local/bin/cua-driver", "call", action, json.dumps(args or {})]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(res.stdout)

def xclick(screen_x, screen_y):
    d = display.Display()
    xtest.fake_input(d, X.MotionNotify, detail=0, x=screen_x, y=screen_y)
    d.sync()
    time.sleep(0.1)
    xtest.fake_input(d, X.ButtonPress, detail=1)
    d.sync()
    time.sleep(0.1)
    xtest.fake_input(d, X.ButtonRelease, detail=1)
    d.sync()
    time.sleep(0.1)

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

    # Click Mode selection (1071, 119)
    print("Clicking Mode selection...")
    xclick(1071, 119)
    time.sleep(1.0)

    # List all windows now
    all_wins = _cua_call("list_windows", {})
    print("\n--- Current Windows ---")
    for w in all_wins.get("windows", []):
        print(f"Title: {w.get('title')}, PID: {w.get('pid')}, WID: {w.get('window_id')}")

if __name__ == "__main__":
    main()
