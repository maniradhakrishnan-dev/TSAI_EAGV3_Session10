import json
import subprocess
import time
from Xlib import X, display
from Xlib.ext import xtest
from Xlib.protocol import event

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
    print(f"Activating Calculator window (pid={pid}, wid={wid}) via EWMH...")
    
    d = display.Display()
    root = d.screen().root
    
    # EWMH Activate
    active_atom = d.intern_atom('_NET_ACTIVE_WINDOW')
    ev = event.ClientMessage(
        window=wid,
        client_type=active_atom,
        data=(32, [1, X.CurrentTime, 0, 0, 0])
    )
    root.send_event(ev, event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask)
    d.sync()
    time.sleep(0.5)

    # Press Ctrl+B using Xlib XTEST
    ctrl_keycode = d.keysym_to_keycode(0xffe3) # Control_L
    b_keycode = d.keysym_to_keycode(0x0062)    # b
    
    print("Pressing Ctrl+B...")
    xtest.fake_input(d, X.KeyPress, ctrl_keycode)
    xtest.fake_input(d, X.KeyPress, b_keycode)
    d.sync()
    time.sleep(0.1)
    
    xtest.fake_input(d, X.KeyRelease, b_keycode)
    xtest.fake_input(d, X.KeyRelease, ctrl_keycode)
    d.sync()
    time.sleep(0.8)

    state = _cua_call("get_window_state", {
        "pid": pid,
        "window_id": wid,
        "capture_mode": "ax"
    })
    
    with open("scratch/calc_ax_after_ctrl_b.txt", "w") as f:
        f.write(state.get("tree_markdown", ""))
    print("AX tree saved to scratch/calc_ax_after_ctrl_b.txt")

if __name__ == "__main__":
    main()
