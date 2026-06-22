import time
from Xlib import X, display
from Xlib.ext import xtest
from Xlib.protocol import event

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
    # Find Calculator window ID
    import json
    import subprocess
    cmd = ["/home/mani_radhakrishnan/.local/bin/cua-driver", "call", "list_windows", "{}"]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    wins = json.loads(res.stdout)
    calc_win = None
    for win in wins.get("windows", []):
        if "calculator" in win.get("title", "").lower():
            calc_win = win
            break
            
    if not calc_win:
        print("Calculator not found!")
        return
        
    wid = calc_win["window_id"]
    print(f"Activating Calculator (wid={wid}) via EWMH...")
    
    # EWMH Activate
    d = display.Display()
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

    # 1. Click Mode selection (1071, 119)
    print("Clicking Mode selection...")
    xclick(1071, 119)
    time.sleep(1.0)

    # 2. Click Basic Mode (1071, 180)
    print("Clicking Basic Mode...")
    xclick(1071, 180)
    time.sleep(1.0)
    print("Done!")

if __name__ == "__main__":
    main()
