#!/usr/bin/env python3
"""Test: activate window via EWMH client message, send Ctrl+L via XTEST, and save."""
import subprocess, json, time, sys, re, os
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
        print(f"  ERR {tool}: {r.stderr.strip()[:200]}")
        return {}
    out = r.stdout.strip()
    return json.loads(out) if out.startswith(("{","[")) else {"raw": out}

def ewmh_activate(window_id):
    """Send _NET_ACTIVE_WINDOW message to root window to focus/raise the window."""
    active_atom = d.intern_atom('_NET_ACTIVE_WINDOW')
    ev = event.ClientMessage(
        window=window_id,
        client_type=active_atom,
        data=(32, [1, X.CurrentTime, 0, 0, 0])  # 1 = source indication (application)
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

def find_window(title_contains):
    for w in cua("list_windows", {}).get("windows", []):
        if title_contains.lower() in w.get("title","").lower():
            return w["pid"], w["window_id"]
    return None, None

def find_idx(tree_md, pattern):
    for line in tree_md.splitlines():
        if re.search(pattern, line, re.IGNORECASE):
            m = re.search(r'\[(\d+)\]', line)
            if m: return int(m.group(1))
    return None

def scan(pid, wid):
    return cua("get_window_state", {"pid": pid, "window_id": wid, "capture_mode": "ax"}).get("tree_markdown", "")

# ─── Clean ───
subprocess.run(["killall", "gedit"], capture_output=True); time.sleep(0.5)

# Launch
cua("launch_app", {"name": "gedit"}); time.sleep(2)
gpid, gwid = find_window("gedit")
print(f"1. gedit pid={gpid} wid={gwid}")

# Type content
tree = scan(gpid, gwid)
text_idx = find_idx(tree, r'\[\d+\].*text.*""')
if text_idx is None:
    for line in tree.splitlines():
        if re.search(r'\[\d+\].*text.*"', line, re.I) and 'search' not in line.lower():
            m = re.search(r'\[(\d+)\]', line)
            if m: text_idx = int(m.group(1)); break

cua("type_text", {"pid": gpid, "window_id": gwid, "element_index": text_idx, "text": "The calculated result is 3298729"})
print("2. Typed content")
time.sleep(0.5)

# Click Save
save_idx = find_idx(tree, r'button.*"Save"')
cua("click", {"pid": gpid, "window_id": gwid, "element_index": save_idx})
time.sleep(2)

dpid, dwid = find_window("Save As")
print(f"3. Dialog wid={dwid}")
if not dwid: sys.exit("FAIL: no dialog")

# ─── EWMH Focus ───
ewmh_activate(dwid)
print("4. Focused Save As dialog via EWMH")
time.sleep(0.5)

# Send Ctrl+L
xkey(XK.XK_l, [XK.XK_Control_L])
print("5. Sent Ctrl+L via XTEST")
time.sleep(0.5)

# Type directory path via cua-driver type_text (global)
dir_path = "/home/mani_radhakrishnan/sandbox_session10/"
cua("type_text", {"pid": dpid, "window_id": dwid, "text": dir_path})
print(f"6. Typed directory path: {dir_path}")
time.sleep(0.3)

# Press Enter to navigate
xkey(XK.XK_Return)
print("7. Pressed Return")
time.sleep(1.5)

# ─── Type Filename ───
# Re-scan to get new state
dtree = scan(dpid, dwid)
fname_idx = find_idx(dtree, r'text.*"Untitled')
if fname_idx is None:
    fname_idx = find_idx(dtree, r'text.*""')
if fname_idx is None:
    for line in dtree.splitlines():
        if re.search(r'\[\d+\].*text.*"', line, re.I) and 'search' not in line.lower():
            m = re.search(r'\[(\d+)\]', line)
            if m: fname_idx = int(m.group(1)); break

print(f"8. Filename field idx={fname_idx}")
cua("click", {"pid": dpid, "window_id": dwid, "element_index": fname_idx})
time.sleep(0.2)
xkey(XK.XK_a, [XK.XK_Control_L])
time.sleep(0.1)
xkey(XK.XK_Delete)
time.sleep(0.1)

cua("type_text", {"pid": dpid, "window_id": dwid, "element_index": fname_idx, "text": "mr_s10_03.txt"})
print("9. Typed filename: mr_s10_03.txt")
time.sleep(0.5)

# Click Save button inside the dialog
dtree2 = scan(dpid, dwid)
dialog_save_idx = None
in_file_chooser = False
for line in dtree2.splitlines():
    if "file chooser" in line.lower() and "save as" in line.lower():
        in_file_chooser = True
        continue
    if in_file_chooser:
        if "save" in line.lower() and "button" in line.lower():
            m = re.search(r'\[(\d+)\]', line)
            if m: dialog_save_idx = int(m.group(1)); break

if dialog_save_idx is None:
    dialog_save_idx = 256

cua("click", {"pid": dpid, "window_id": dwid, "element_index": dialog_save_idx})
print(f"10. Clicked dialog Save button (idx={dialog_save_idx})")
time.sleep(2)

# Verify
target = "/home/mani_radhakrishnan/sandbox_session10/mr_s10_03.txt"
if os.path.exists(target):
    print(f"\n✅ SUCCESS! {target}")
    print(f"   Content: {open(target).read()!r}")
else:
    print(f"\n❌ NOT at {target}")
    import glob
    for p in glob.glob("/home/mani_radhakrishnan/*mr_s10*"):
        print(f"   Home: {p}")

subprocess.run(["killall", "gedit"], capture_output=True)
