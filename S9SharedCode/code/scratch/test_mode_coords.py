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
    # Move
    xtest.fake_input(d, X.MotionNotify, detail=0, x=screen_x, y=screen_y)
    d.sync()
    time.sleep(0.1)
    # Press
    xtest.fake_input(d, X.ButtonPress, detail=1)
    d.sync()
    time.sleep(0.1)
    # Release
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
    print(f"Calculator: pid={pid}, wid={wid}")

    # Focus the window using X11 EWMH
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

    # Get structured window state (which contains coordinates of elements)
    state = _cua_call("get_window_state", {
        "pid": pid,
        "window_id": wid,
        "capture_mode": "ax"
    })
    
    # We want to find element index 4 (Mode selection)
    # Let's search the list of elements for index 4 or name "Mode selection"
    elements = state.get("elements", [])
    mode_btn = None
    for el in elements:
        if el.get("index") == 4 or el.get("name") == "Mode selection":
            mode_btn = el
            break

    if not mode_btn:
        print("Mode selection button not found in elements!")
        # Let's print some elements to understand schema
        if elements:
            print("First element sample:", elements[0])
        return

    print("Found Mode selection button:", mode_btn)
    # Get bounds
    # Usually: {'x': ..., 'y': ..., 'width': ..., 'height': ...}
    # Wait, are these window-local or screen-global?
    # Let's check!
    # Let's print it:
    x = mode_btn.get("x", 0)
    y = mode_btn.get("y", 0)
    w = mode_btn.get("width", 0)
    h = mode_btn.get("height", 0)
    
    # Let's click at the center of the element
    cx = x + w // 2
    cy = y + h // 2
    
    print(f"Clicking Mode selection at ({cx}, {cy})...")
    xclick(cx, cy)
    time.sleep(1.0)

    # Now get new state to find "Basic Mode"
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
        print("Basic Mode button not found in open menu!")
        # Print list of element names
        names = [el.get("name") for el in state2.get("elements", []) if el.get("name")]
        print("Available element names:", names)
        return

    bx = basic_btn.get("x", 0)
    by = basic_btn.get("y", 0)
    bw = basic_btn.get("width", 0)
    bh = basic_btn.get("height", 0)
    bcx = bx + bw // 2
    bcy = by + bh // 2

    print(f"Clicking Basic Mode at ({bcx}, {bcy})...")
    xclick(bcx, bcy)
    time.sleep(1.0)
    print("Done! Check if it switched mode.")

if __name__ == "__main__":
    main()
