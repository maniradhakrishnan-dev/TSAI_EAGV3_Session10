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
subprocess.run(["killall", "gnome-calculator"], capture_output=True)
time.sleep(0.5)
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

print(f"Calculator pid={pid} wid={w_id}")
state = cua("get_window_state", {"pid": pid, "window_id": w_id, "capture_mode": "ax"})
print("--- AX TREE ---")
for line in state.get("tree_markdown", "").splitlines():
    if any(x in line.lower() for x in ('"7"', '"8"', '"multiply"', '"equals"', '"clear"', 'push button')):
        print(line.strip())

subprocess.run(["killall", "gnome-calculator"], capture_output=True)
