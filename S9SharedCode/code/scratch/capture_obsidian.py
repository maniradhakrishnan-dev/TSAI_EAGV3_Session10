#!/usr/bin/env python3
"""Capture Obsidian window screenshot to diagnose state."""
import subprocess, json, time, os

CUA = os.path.expanduser("~/.local/bin/cua-driver")

def cua(tool, args):
    r = subprocess.run([CUA, "call", tool, json.dumps(args)],
                       capture_output=True, text=True, timeout=30)
    return json.loads(r.stdout) if r.stdout.strip().startswith("{") else {}

# Launch
subprocess.Popen(["obsidian", "--remote-debugging-port=9222"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(5)

# Find window
w_id = None
for w in cua("list_windows", {}).get("windows", []):
    if "obsidian" in w.get("title","").lower():
        w_id = w["window_id"]
        pid = w["pid"]
        break

if w_id:
    # Capture vision
    out_img = "/home/mani_radhakrishnan/.gemini/antigravity/brain/1127d650-97f7-4389-a0d0-0c4991946c47/obsidian_screenshot.png"
    cua("get_window_state", {
        "pid": pid,
        "window_id": w_id,
        "capture_mode": "vision",
        "screenshot_out_file": out_img
    })
    print(f"Captured to {out_img}")
else:
    print("Obsidian window not found")

# Kill
subprocess.run(["killall", "-9", "obsidian"])
