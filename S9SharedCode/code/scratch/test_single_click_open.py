#!/usr/bin/env python3
"""Test: click folder once, then click the dialog's Save/Open button (idx=256) without killing gedit at the end."""
import subprocess, json, time, sys, re, os

CUA = os.path.expanduser("~/.local/bin/cua-driver")

def cua(tool, args):
    r = subprocess.run([CUA, "call", tool, json.dumps(args)],
                       capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        print(f"  ERR {tool}: {r.stderr.strip()[:200]}")
        return {}
    out = r.stdout.strip()
    return json.loads(out) if out.startswith(("{","[")) else {"raw": out}

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

# Click Save
tree = scan(gpid, gwid)
save_idx = find_idx(tree, r'button.*"Save"')
cua("click", {"pid": gpid, "window_id": gwid, "element_index": save_idx})
time.sleep(2)

dpid, dwid = find_window("Save As")
print(f"2. Dialog wid={dwid}")

# ─── Step 1: Click the 'mani_radhakrishnan' breadcrumb to navigate to home ───
dtree = scan(dpid, dwid)
home_idx = find_idx(dtree, r'button.*"mani_radhakrishnan"')
if home_idx is None:
    home_idx = find_idx(dtree, r'button.*"home"')
print(f"3. Home breadcrumb idx={home_idx}")
cua("click", {"pid": dpid, "window_id": dwid, "element_index": home_idx})
time.sleep(1.5)

# ─── Step 2: Click sandbox_session10 folder once ───
dtree2 = scan(dpid, dwid)
sandbox_idx = find_idx(dtree2, r'table cell.*"sandbox_session10"')
print(f"4. sandbox_session10 folder idx={sandbox_idx}")
if sandbox_idx is None:
    sys.exit("FAIL: sandbox_session10 not found in list")

cua("click", {"pid": dpid, "window_id": dwid, "element_index": sandbox_idx})
print("5. Clicked sandbox_session10 folder once")
time.sleep(1.5)

# ─── Step 3: Find the correct dialog Save button ───
dtree3 = scan(dpid, dwid)
dialog_save_idx = None
lines = dtree3.splitlines()
in_file_chooser = False
for line in lines:
    if "file chooser" in line.lower() and "save as" in line.lower():
        in_file_chooser = True
        continue
    if in_file_chooser:
        if "save" in line.lower() and "button" in line.lower():
            m = re.search(r'\[(\d+)\]', line)
            if m:
                dialog_save_idx = int(m.group(1))
                print(f"   Found dialog Save button under file chooser: {line.strip()}")
                break

if dialog_save_idx is None:
    dialog_save_idx = 256  # fallback

cua("click", {"pid": dpid, "window_id": dwid, "element_index": dialog_save_idx})
print(f"6. Clicked dialog Save/Open button (idx={dialog_save_idx})")
time.sleep(1.5)

# ─── Step 4: Verify ───
dtree4 = scan(dpid, dwid)
sandbox_breadcrumb = find_idx(dtree4, r'button.*"sandbox_session10"')
print(f"7. sandbox_session10 breadcrumb after open: {sandbox_breadcrumb}")
# Print the window list to see if the Save As dialog is still open
print("8. Active windows now:")
for w in cua("list_windows", {}).get("windows", []):
    if "gedit" in w.get("title","").lower() or "save as" in w.get("title","").lower():
        print(f"   - {w.get('title')} (wid={w.get('window_id')})")

# DO NOT KILL GEDIT
