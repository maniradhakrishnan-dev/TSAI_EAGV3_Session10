#!/usr/bin/env python3
"""Test: simplest possible approach — AT-SPI click filename field, clear it via
XTEST Ctrl+A, then AT-SPI type_text the full path, then click Save.

GTK's file chooser should resolve the full path when Save is clicked.
"""
import subprocess, json, time, sys, re, os
from Xlib import X, display, XK
from Xlib.ext import xtest

CUA = os.path.expanduser("~/.local/bin/cua-driver")
d = display.Display()

def cua(tool, args):
    r = subprocess.run([CUA, "call", tool, json.dumps(args)],
                       capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        print(f"  ERR {tool}: {r.stderr.strip()[:200]}")
        return {}
    out = r.stdout.strip()
    return json.loads(out) if out.startswith(("{","[")) else {"raw": out}

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

# ─── 1. Launch & type content ───
cua("launch_app", {"name": "gedit"}); time.sleep(2)
gpid, gwid = find_window("gedit")
print(f"1. gedit pid={gpid} wid={gwid}")

tree = scan(gpid, gwid)
text_idx = find_idx(tree, r'\[\d+\].*text.*""')
if text_idx is None:
    for line in tree.splitlines():
        if re.search(r'\[\d+\].*text.*"', line, re.I) and 'search' not in line.lower():
            m = re.search(r'\[(\d+)\]', line)
            if m: text_idx = int(m.group(1)); break

cua("type_text", {"pid": gpid, "window_id": gwid, "element_index": text_idx, "text": "The calculated result is 3298729"})
print(f"2. Typed content")
time.sleep(0.5)

# ─── 3. Click Save ───
tree = scan(gpid, gwid)
save_idx = find_idx(tree, r'push button.*"Save"')
cua("click", {"pid": gpid, "window_id": gwid, "element_index": save_idx})
print(f"3. Clicked Save"); time.sleep(2)

# ─── 4. Find dialog ───
dpid, dwid = None, None
for _ in range(10):
    dpid, dwid = find_window("Save As")
    if dwid: break; time.sleep(0.3)
print(f"4. Dialog wid={dwid}"); time.sleep(0.5)

# ─── 5. Focus the Save As window via XTEST ───
xwin = d.create_resource_object('window', dwid)
xwin.set_input_focus(X.RevertToParent, X.CurrentTime)
d.sync(); time.sleep(0.3)

# ─── 6. Find filename field, click it, clear it with XTEST Ctrl+A, Delete ───
dtree = scan(dpid, dwid)
fname_idx = find_idx(dtree, r'text.*"Untitled')
print(f"5. Filename idx={fname_idx}")

cua("click", {"pid": dpid, "window_id": dwid, "element_index": fname_idx})
time.sleep(0.2)

# Select all and delete using XTEST (real keypress, GTK accepts it)
xkey(XK.XK_a, [XK.XK_Control_L])
time.sleep(0.1)
xkey(XK.XK_Delete)
time.sleep(0.1)

# Verify field is empty
dtree_check = scan(dpid, dwid)
fname_check = find_idx(dtree_check, r'text.*"Untitled')
fname_check2 = find_idx(dtree_check, r'text.*""')
print(f"   After clear: Untitled idx={fname_check}, empty idx={fname_check2}")

# ─── 7. Type FULL PATH via AT-SPI type_text ───
full_path = "/home/mani_radhakrishnan/sandbox_session10/mr_s10_03.txt"
cua("type_text", {"pid": dpid, "window_id": dwid, "element_index": fname_idx, "text": full_path})
print(f"6. Typed full path into field (idx={fname_idx})")
time.sleep(0.5)

# Verify
dtree_v = scan(dpid, dwid)
for line in dtree_v.splitlines():
    if "sandbox" in line.lower() or "mr_s10" in line.lower():
        print(f"   Verify: {line.strip()[:120]}")

# ─── 8. Click Save ───
save_idx2 = find_idx(dtree_v, r'push button.*"Save"')
print(f"7. Save button idx={save_idx2}")
cua("click", {"pid": dpid, "window_id": dwid, "element_index": save_idx2})
print("   Clicked Save!"); time.sleep(2)

# ─── 9. Check for error dialogs ───
_, errwid = find_window("error")
if errwid:
    print(f"   Error dialog found: wid={errwid}")
    errtree = scan(dpid, errwid)
    for line in errtree.splitlines():
        if "label" in line.lower() or "error" in line.lower():
            print(f"   {line.strip()[:120]}")

# ─── 10. Result ───
target = "/home/mani_radhakrishnan/sandbox_session10/mr_s10_03.txt"
if os.path.exists(target):
    print(f"\n✅ SUCCESS! {target}")
    print(f"   Content: {open(target).read()!r}")
else:
    print(f"\n❌ NOT at {target}")
    # Search everywhere
    import glob
    for p in glob.glob("/home/mani_radhakrishnan/**/mr_s10*", recursive=True):
        print(f"   Found: {p}")

subprocess.run(["killall", "gedit"], capture_output=True)
