import pyatspi
import time
import sys
import json
import subprocess
from Xlib import X, display
from Xlib.ext import xtest
from Xlib.protocol import event

def find_element(element, name):
    if not element:
        return None
    try:
        el_name = element.name
    except Exception:
        el_name = ""
    if el_name == name:
        return element
    try:
        child_count = element.childCount
    except Exception:
        child_count = 0
    for i in range(child_count):
        try:
            child = element.getChildAtIndex(i)
            res = find_element(child, name)
            if res:
                return res
        except Exception:
            continue
    return None

def xclick(d, screen_x, screen_y):
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
    reg = pyatspi.Registry
    desktop = reg.getDesktop(0)
    calc_app = None
    for app in desktop:
        if app and app.name in ["gnome-calculator", "Calculator"]:
            calc_app = app
            break
            
    if not calc_app:
        print("Calculator not found in AT-SPI")
        sys.exit(0)

    # Focus the window using cua-driver first
    try:
        cmd = ["/home/mani_radhakrishnan/.local/bin/cua-driver", "call", "list_windows", "{}"]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        wins = json.loads(res.stdout)
        calc_win = None
        for win in wins.get("windows", []):
            if "calculator" in win.get("title", "").lower():
                calc_win = win
                break
        if calc_win:
            wid = calc_win["window_id"]
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
    except Exception as fe:
        print(f"Warning: Failed to focus window: {fe}")

    # Check if converter or advanced mode is open
    has_advanced = find_element(calc_app, "Exponent") or find_element(calc_app, "√") or find_element(calc_app, "Angle")
    if not has_advanced:
        print("Calculator is already in Basic Mode")
        sys.exit(0)

    # Find Mode selection button
    mode_sel = find_element(calc_app, "Mode selection")
    if not mode_sel:
        print("Mode selection button not found!")
        sys.exit(1)
        
    comp = mode_sel.queryComponent()
    ext = comp.getExtents(pyatspi.XY_SCREEN)
    ms_x = ext.x + ext.width // 2
    ms_y = ext.y + ext.height // 2
    
    d = display.Display()
    
    # Click Mode selection
    print(f"Clicking Mode selection at ({ms_x}, {ms_y})...")
    xclick(d, ms_x, ms_y)
    time.sleep(1.0)
    
    # Find Basic Mode button
    basic_mode = find_element(calc_app, "Basic Mode")
    if not basic_mode:
        print("Basic Mode button not found in open menu!")
        sys.exit(1)
        
    comp_bm = basic_mode.queryComponent()
    ext_bm = comp_bm.getExtents(pyatspi.XY_SCREEN)
    bm_x = ext_bm.x + ext_bm.width // 2
    bm_y = ext_bm.y + ext_bm.height // 2
    
    print(f"Clicking Basic Mode at ({bm_x}, {bm_y})...")
    xclick(d, bm_x, bm_y)
    time.sleep(1.0)
    print("Successfully switched to Basic Mode.")

if __name__ == "__main__":
    main()
