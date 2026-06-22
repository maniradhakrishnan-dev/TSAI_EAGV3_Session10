import subprocess, json, time, os, sys

CUA = os.path.expanduser("~/.local/bin/cua-driver")

def cua(tool, args):
    r = subprocess.run([CUA, "call", tool, json.dumps(args)],
                       capture_output=True, text=True, timeout=30)
    print(f"--- {tool} output ---")
    print("STDOUT:", r.stdout.strip())
    print("STDERR:", r.stderr.strip())
    if r.returncode != 0:
        print(f"Error code: {r.returncode}")
    out = r.stdout.strip()
    return json.loads(out) if out.startswith(("{","[")) else {"raw": out}

# Clean
subprocess.run(["killall", "-9", "obsidian"], capture_output=True)
time.sleep(0.5)

# Kill existing daemon to reload environment variables
print("Stopping cua-driver daemon...")
subprocess.run([CUA, "status"], capture_output=True) # Check status
subprocess.run(["killall", "cua-driver"], capture_output=True)
time.sleep(0.5)

# Set CDP port and start daemon
os.environ["CUA_DRIVER_CDP_PORT"] = "9222"
print("Starting cua-driver serve daemon with CUA_DRIVER_CDP_PORT=9222...")
subprocess.Popen([CUA, "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.5)

# Launch Obsidian
print("Launching Obsidian with remote debugging port...")
proc = subprocess.Popen(["obsidian", "--remote-debugging-port=9222"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(6.0)

# Find pid
w_id = None
pid = None
for w in cua("list_windows", {}).get("windows", []):
    title = w.get("title","").lower()
    if "terminal" in title or "bash" in title or "searchpad" in title:
        continue
    if "obsidian" in title:
        w_id = w["window_id"]
        pid = w["pid"]
        break

if not pid or not w_id:
    print("Obsidian not found!")
    sys.exit(1)

print(f"Found Obsidian pid={pid} wid={w_id}")

# Try calling page tool
print("\n1. Testing page tool click_element action...")
cua("page", {
    "pid": pid,
    "window_id": w_id,
    "action": "click_element",
    "selector": "body"
})

print("\n2. Testing page tool execute_javascript action...")
cua("page", {
    "pid": pid,
    "window_id": w_id,
    "action": "execute_javascript",
    "javascript": "typeof app"
})

print("\n2b. Testing async IIFE writing content...")
cua("page", {
    "pid": pid,
    "window_id": w_id,
    "action": "execute_javascript",
    "javascript": """
(async () => {
  try {
    let title = "cdp_test.md";
    let file = app.vault.getAbstractFileByPath(title);
    if (file) {
      await app.vault.modify(file, "Updated content!");
    } else {
      await app.vault.create(title, "Created content!");
    }
    return "OK";
  } catch(e) {
    return e.toString();
  }
})()
"""
})

print("\n3. Testing page tool query_dom action...")
cua("page", {
    "pid": pid,
    "window_id": w_id,
    "action": "query_dom",
    "selector": "body"
})

print("\n4. Testing page tool get_text action...")
cua("page", {
    "pid": pid,
    "window_id": w_id,
    "action": "get_text",
    "selector": "body"
})

# Kill
subprocess.run(["killall", "-9", "obsidian"])
