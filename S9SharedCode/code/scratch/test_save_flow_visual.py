#!/usr/bin/env python3
import asyncio
import json
import os
import sys
import time
import subprocess
from pathlib import Path
from Xlib import X, display, XK
from Xlib.ext import xtest
from Xlib.protocol import event

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from computer.skill import _cua_call, _ensure_daemon

def send_key(d, keysym, mods=None):
    keycode = d.keysym_to_keycode(keysym)
    mcs = [d.keysym_to_keycode(m) for m in (mods or [])]
    for mc in mcs:
        xtest.fake_input(d, X.KeyPress, mc)
    xtest.fake_input(d, X.KeyPress, keycode)
    d.sync()
    time.sleep(0.05)
    xtest.fake_input(d, X.KeyRelease, keycode)
    for mc in reversed(mcs):
        xtest.fake_input(d, X.KeyRelease, mc)
    d.sync()

def ewmh_activate(d, window_id):
    root = d.screen().root
    active_atom = d.intern_atom('_NET_ACTIVE_WINDOW')
    ev = event.ClientMessage(
        window=window_id,
        client_type=active_atom,
        data=(32, [1, X.CurrentTime, 0, 0, 0])
    )
    root.send_event(ev, event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask)
    d.sync()

async def main():
    _ensure_daemon()
    d = display.Display()
    
    # Clean gedit
    subprocess.run(["killall", "gedit"], capture_output=True)
    await asyncio.sleep(0.5)
    
    # Launch gedit
    env = dict(os.environ)
    env["DISPLAY"] = os.environ.get("DISPLAY", ":0")
    proc = subprocess.Popen(["gedit"], env=env)
    gpid = proc.pid
    print(f"1. Launched gedit, PID: {gpid}")
    await asyncio.sleep(2.0)
    
    # Find window
    gwid = None
    for _ in range(10):
        for w in _cua_call("list_windows", {}).get("windows", []):
            if w.get("pid") == gpid:
                gwid = w["window_id"]
                break
        if gwid: break
        await asyncio.sleep(0.3)
    
    if not gwid:
        print("FAIL: No gedit window")
        return
        
    print(f"2. Found window: {gwid}")
    ewmh_activate(d, gwid)
    await asyncio.sleep(0.5)
    
    # Click and type text
    import re
    text_idx = None
    save_idx = None
    for attempt in range(20):
        state = _cua_call("get_window_state", {"pid": gpid, "window_id": gwid, "capture_mode": "ax"})
        tree_md = state.get("tree_markdown", "")
        elem_count = state.get("element_count", 0)
        
        # Search for text area using the exact logic from test_ewmh_save.py
        for line in tree_md.splitlines():
            if 'text' in line.lower() and '""' in line and '[' in line and 'search' not in line.lower():
                m = re.search(r'\[(\d+)\]', line)
                if m:
                    text_idx = int(m.group(1))
                    break
        if text_idx is None:
            for line in tree_md.splitlines():
                if re.search(r'\[\d+\].*text.*"', line, re.I) and 'search' not in line.lower():
                    m = re.search(r'\[(\d+)\]', line)
                    if m:
                        text_idx = int(m.group(1))
                        break
        
        # Search for Save button
        for line in tree_md.splitlines():
            if "save" in line.lower() and "button" in line.lower() and '[' in line:
                m = re.search(r'\[(\d+)\]', line)
                if m:
                    save_idx = int(m.group(1))
                    break
                    
        if text_idx is not None and save_idx is not None:
            break
        await asyncio.sleep(0.5)
                
    if text_idx is None:
        print("FAIL: No text area index")
        return
        
    _cua_call("type_text", {"pid": gpid, "window_id": gwid, "element_index": text_idx, "text": "Visual test content"})
    print("3. Typed text")
    await asyncio.sleep(0.5)
    
    if save_idx is None:
        print("FAIL: No Save button index")
        return
        
    _cua_call("click", {"pid": gpid, "window_id": gwid, "element_index": save_idx})
    print("4. Clicked Save button, waiting for dialog...")
    await asyncio.sleep(2.0)
    
    # Find Save As dialog
    dwid = None
    dpid = None
    for _ in range(10):
        for w in _cua_call("list_windows", {}).get("windows", []):
            if "save as" in w.get("title", "").lower():
                dwid = w["window_id"]
                dpid = w.get("pid")
                break
        if dwid: break
        await asyncio.sleep(0.3)
        
    if not dwid:
        print("FAIL: No Save As dialog found")
        return
        
    print(f"5. Found Save As dialog, wid: {dwid}")
    
    # Screenshot 1: dialog open
    _cua_call("take_screenshot", {"output_path": "/home/mani_radhakrishnan/TSAI_EAGV3_Session10/S9SharedCode/code/state/shot1_open.png"})
    print("Screenshot 1 taken")
    
    ewmh_activate(d, dwid)
    await asyncio.sleep(0.5)
    
    # Send Ctrl+L
    send_key(d, XK.XK_l, [XK.XK_Control_L])
    print("6. Sent Ctrl+L")
    await asyncio.sleep(0.5)
    
    # Screenshot 2: Ctrl+L location bar open
    _cua_call("take_screenshot", {"output_path": "/home/mani_radhakrishnan/TSAI_EAGV3_Session10/S9SharedCode/code/state/shot2_ctrl_l.png"})
    print("Screenshot 2 taken")
    
    # Type full path
    full_path = "/home/mani_radhakrishnan/sandbox_session10/mr_s10_03.txt"
    _cua_call("type_text", {"pid": dpid, "window_id": dwid, "text": full_path})
    print(f"7. Typed full path: {full_path}")
    await asyncio.sleep(0.5)
    
    # Screenshot 3: path typed
    _cua_call("take_screenshot", {"output_path": "/home/mani_radhakrishnan/TSAI_EAGV3_Session10/S9SharedCode/code/state/shot3_typed.png"})
    print("Screenshot 3 taken")
    
    # Press Return
    send_key(d, XK.XK_Return)
    print("8. Pressed Return")
    await asyncio.sleep(1.0)
    
    # Screenshot 4: after first Return
    _cua_call("take_screenshot", {"output_path": "/home/mani_radhakrishnan/TSAI_EAGV3_Session10/S9SharedCode/code/state/shot4_after_return.png"})
    print("Screenshot 4 taken")
    
    # Press Return again (in case it navigates first)
    send_key(d, XK.XK_Return)
    print("9. Pressed Return again")
    await asyncio.sleep(1.0)
    
    # Screenshot 5: after second Return
    _cua_call("take_screenshot", {"output_path": "/home/mani_radhakrishnan/TSAI_EAGV3_Session10/S9SharedCode/code/state/shot5_after_return2.png"})
    print("Screenshot 5 taken")
    
    # Check if file exists
    if os.path.exists(full_path):
        print(f"✅ SUCCESS! Saved to {full_path}")
    else:
        print("❌ FAILED to save")
        
    subprocess.run(["killall", "gedit"], capture_output=True)

if __name__ == "__main__":
    asyncio.run(main())
