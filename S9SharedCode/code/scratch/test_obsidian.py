#!/usr/bin/env python3
"""Test: Launch Obsidian, focus it, create a new note, write content using XTEST typing, and save."""
import subprocess, json, time, sys, os
from Xlib import X, display, XK
from Xlib.ext import xtest
from Xlib.protocol import event

CUA = os.path.expanduser("~/.local/bin/cua-driver")
d = display.Display()
root = d.screen().root

def cua(tool, args):
    r = subprocess.run([CUA, "call", tool, json.dumps(args)],
                       capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        return {}
    out = r.stdout.strip()
    return json.loads(out) if out.startswith(("{","[")) else {"raw": out}

def ewmh_activate(window_id):
    active_atom = d.intern_atom('_NET_ACTIVE_WINDOW')
    ev = event.ClientMessage(
        window=window_id,
        client_type=active_atom,
        data=(32, [1, X.CurrentTime, 0, 0, 0])
    )
    root.send_event(ev, event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask)
    d.sync()

def xkey(keysym, mods=None):
    keycode = d.keysym_to_keycode(keysym)
    mcs = [d.keysym_to_keycode(m) for m in (mods or [])]
    for mc in mcs: xtest.fake_input(d, X.KeyPress, mc)
    xtest.fake_input(d, X.KeyPress, keycode)
    d.sync(); time.sleep(0.05)
    xtest.fake_input(d, X.KeyRelease, keycode)
    for mc in reversed(mcs): xtest.fake_input(d, X.KeyRelease, mc)
    d.sync()

def xtest_type(d, text_str):
    for char in text_str:
        shift_req = False
        keysym = None
        
        # Check special characters
        shift_chars = '!@#$%^&*()_+{}|:"<>?~'
        if char.isupper() or char in shift_chars:
            shift_req = True
            
        keysym = XK.string_to_keysym(char)
        if keysym == 0:
            keysym = ord(char)
            
        keycode = d.keysym_to_keycode(keysym)
        
        # Press Shift if required
        if shift_req:
            shift_keycode = d.keysym_to_keycode(XK.XK_Shift_L)
            xtest.fake_input(d, X.KeyPress, shift_keycode)
            d.sync()
            
        # Press and release keycode
        xtest.fake_input(d, X.KeyPress, keycode)
        d.sync()
        time.sleep(0.02)
        xtest.fake_input(d, X.KeyRelease, keycode)
        d.sync()
        
        # Release Shift if required
        if shift_req:
            xtest.fake_input(d, X.KeyRelease, shift_keycode)
            d.sync()
            
        time.sleep(0.01)

def find_window(title_contains):
    for w in cua("list_windows", {}).get("windows", []):
        if title_contains.lower() in w.get("title","").lower():
            return w["pid"], w["window_id"]
    return None, None

# Clean
subprocess.run(["killall", "-9", "obsidian"], capture_output=True); time.sleep(0.5)

# Launch
print("1. Launching Obsidian...")
subprocess.Popen(["obsidian", "--remote-debugging-port=9222"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(5)

opid, owid = find_window("Obsidian")
print(f"2. Obsidian pid={opid} wid={owid}")
if not owid:
    sys.exit("FAIL: Obsidian window not found")

# Focus
ewmh_activate(owid)
print("3. Focused Obsidian window")
time.sleep(1.0)

# Create a new note using Ctrl+N
xkey(XK.XK_n, [XK.XK_Control_L])
print("4. Sent Ctrl+N")
time.sleep(1.0)

# Type title using XTEST
title_text = "mr_s10_obsidian_test"
xtest_type(d, title_text)
print(f"5. Typed title: {title_text}")
time.sleep(0.5)

# Press Enter to go to content
xkey(XK.XK_Return)
time.sleep(0.5)

# Type note content using XTEST
note_content = "This is a test note created in Obsidian by the agent."
xtest_type(d, note_content)
print("6. Typed content")
time.sleep(0.5)

# Save (Obsidian auto-saves, but Ctrl+S commits it)
xkey(XK.XK_s, [XK.XK_Control_L])
print("7. Sent Ctrl+S")
time.sleep(1.0)

# Verify
target_file = "/home/mani_radhakrishnan/Obsidian Vault/mr_s10_obsidian_test.md"
if os.path.exists(target_file):
    print(f"\n✅ SUCCESS! Obsidian note created at {target_file}")
    print(f"   Content: {open(target_file).read()!r}")
else:
    print(f"\n❌ FAILED: Note not found at {target_file}")

# Kill
subprocess.run(["killall", "-9", "obsidian"], capture_output=True)
