#!/usr/bin/env python3
import asyncio
import json
import os
import sys
import time
import subprocess
from pathlib import Path
from Xlib import X, display, XK
from Xlib.protocol import event

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from computer.skill import _cua_call, _ensure_daemon

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
    state = _cua_call("get_window_state", {"pid": gpid, "window_id": gwid, "capture_mode": "ax"})
    tree_md = state.get("tree_markdown", "")
    
    import re
    text_idx = None
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
        
    if text_idx is None:
        print("FAIL: No text area index")
        return
        
    _cua_call("type_text", {"pid": gpid, "window_id": gwid, "element_index": text_idx, "text": "Visual test content"})
    print("3. Typed text")
    await asyncio.sleep(0.5)
    
    # Click Save
    save_idx = None
    for line in tree_md.splitlines():
        if "save" in line.lower() and "button" in line.lower() and '[' in line:
            m = re.search(r'\[(\d+)\]', line)
            if m:
                save_idx = int(m.group(1))
                break
                
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
    ewmh_activate(d, dwid)
    await asyncio.sleep(0.5)
    
    # Type full path using PyAutoGUI
    import pyautogui
    full_path = "/home/mani_radhakrishnan/sandbox_session10/mr_s10_03.txt"
    try:
        os.remove(full_path)
    except FileNotFoundError:
        pass
        
    print("6. Typing full path via PyAutoGUI...")
    pyautogui.write(full_path)
    await asyncio.sleep(0.5)
    
    print("7. Pressing enter...")
    pyautogui.press("enter")
    await asyncio.sleep(1.0)
    
    # Check if saved
    if os.path.exists(full_path):
        print(f"✅ SUCCESS! Saved to {full_path}")
    else:
        print("❌ FAILED to save")
        
    subprocess.run(["killall", "gedit"], capture_output=True)

if __name__ == "__main__":
    asyncio.run(main())
