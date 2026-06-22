#!/usr/bin/env python3
"""Test: can we double-click the sandbox_session10 folder in the file list using count=2?"""
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
    # try 'home'
    home_idx = find_idx(dtree, r'button.*"home"')
print(f"3. Home breadcrumb idx={home_idx}")
cua("click", {"pid": dpid, "window_id": dwid, "element_index": home_idx})
time.sleep(1.5)

# ─── Step 2: Find sandbox_session10 in the list ───
dtree2 = scan(dpid, dwid)
sandbox_idx = find_idx(dtree2, r'table cell.*"sandbox_session10"')
print(f"4. sandbox_session10 folder idx={sandbox_idx}")
if sandbox_idx is None:
    print("   sandbox_session10 not found in list. printing parts of tree:")
    for line in dtree2.splitlines():
        if "sandbox" in line.lower() or "table cell" in line.lower():
            print(f"     {line.strip()[:100]}")
    sys.exit(1)

# ─── Step 3: Double click sandbox_session10 ───
print(f"5. Double-clicking sandbox_session10 (idx={sandbox_idx})")
cua("click", {"pid": dpid, "window_id": dwid, "element_index": sandbox_idx, "count": 2})
time.sleep(1.5)

# ─── Step 4: Verify we are inside sandbox_session10 ───
dtree3 = scan(dpid, dwid)
# If we entered, there should be a breadcrumb for sandbox_session10 at the top
sandbox_breadcrumb = find_idx(dtree3, r'button.*"sandbox_session10"')
print(f"6. sandbox_session10 breadcrumb after double-click: {sandbox_breadcrumb}")

if sandbox_breadcrumb is not None:
    print("✅ SUCCESS! Entered the folder.")
else:
    print("❌ FAILED to enter the folder.")

subprocess.run(["killall", "gedit"], capture_output=True)
