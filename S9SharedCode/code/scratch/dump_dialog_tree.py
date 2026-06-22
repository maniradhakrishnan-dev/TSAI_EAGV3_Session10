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
    print(f"Launched gedit, PID: {gpid}")
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
        
    ewmh_activate(d, gwid)
    await asyncio.sleep(0.5)
    
    # Click Save
    state = _cua_call("get_window_state", {"pid": gpid, "window_id": gwid, "capture_mode": "ax"})
    tree_md = state.get("tree_markdown", "")
    
    import re
    save_idx = None
    for line in tree_md.splitlines():
        if "save" in line.lower() and "push button" in line.lower():
            m = re.search(r'\[(\d+)\]', line)
            if m:
                save_idx = int(m.group(1))
                break
                
    if save_idx is None:
        print("FAIL: No Save button index")
        return
        
    _cua_call("click", {"pid": gpid, "window_id": gwid, "element_index": save_idx})
    print("Clicked Save button, waiting for dialog...")
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
        
    print(f"Found Save As dialog, wid: {dwid}")
    ewmh_activate(d, dwid)
    await asyncio.sleep(0.5)
    
    # Send Ctrl+L
    send_key(d, XK.XK_l, [XK.XK_Control_L])
    print("Sent Ctrl+L")
    await asyncio.sleep(0.5)
    
    # Type full path
    full_path = "/home/mani_radhakrishnan/sandbox_session10/mr_s10_03.txt"
    _cua_call("type_text", {"pid": dpid, "window_id": dwid, "text": full_path})
    print(f"Typed full path: {full_path}")
    await asyncio.sleep(0.5)
    
    # Get AX tree before Return
    tree_before = _cua_call("get_window_state", {"pid": dpid, "window_id": dwid, "capture_mode": "ax"}).get("tree_markdown", "")
    print("\n--- AX TREE BEFORE RETURN ---")
    for line in tree_before.splitlines():
        if '[' in line:
            print(line[:120])
            
    # Press Return
    send_key(d, XK.XK_Return)
    print("\nPressed Return once")
    await asyncio.sleep(1.5)
    
    # Get AX tree after Return
    tree_after = _cua_call("get_window_state", {"pid": dpid, "window_id": dwid, "capture_mode": "ax"}).get("tree_markdown", "")
    print("\n--- AX TREE AFTER RETURN ---")
    for line in tree_after.splitlines():
        if '[' in line:
            print(line[:120])
            
    # Clean up gedit
    subprocess.run(["killall", "gedit"], capture_output=True)

if __name__ == "__main__":
    asyncio.run(main())
