#!/usr/bin/env python3
import subprocess, json, time, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CUA = os.path.expanduser("~/.local/bin/cua-driver")

def cua(tool, args):
    r = subprocess.run([CUA, "call", tool, json.dumps(args)],
                       capture_output=True, text=True, timeout=30)
    out = r.stdout.strip()
    return json.loads(out) if out.startswith(("{","[")) else {"raw": out}

# Launch
subprocess.Popen(["gnome-calculator"])
time.sleep(2.0)

# Find window
w_id = None
pid = None
for w in cua("list_windows", {}).get("windows", []):
    if "calculator" in w.get("title","").lower():
        w_id = w["window_id"]
        pid = w["pid"]
        break

if not w_id:
    print("Calculator not found!")
    sys.exit(1)

state = cua("get_window_state", {"pid": pid, "window_id": w_id, "capture_mode": "ax"})

# The window state return JSON has a key named "elements" which is a list of all elements,
# including their bounding box coords!
elements = state.get("elements", [])
print(f"Total elements: {len(elements)}")

for el in elements:
    name = el.get("name") or ""
    role = el.get("role") or ""
    idx = el.get("index")
    # Get bounding box
    bbox = el.get("bbox") or {} # or bounding_box or x,y,w,h
    x = el.get("x")
    y = el.get("y")
    w = el.get("width")
    h = el.get("height")
    
    if name in ("7", "8", "×", "=", "C", "9", "6", "5", "4") or "multiply" in name.lower() or "equals" in name.lower():
        print(f"Element [{idx}] Role={role} Name='{name}' Box: x={x}, y={y}, w={w}, h={h}, bbox={bbox}")

subprocess.run(["killall", "gnome-calculator"], capture_output=True)
