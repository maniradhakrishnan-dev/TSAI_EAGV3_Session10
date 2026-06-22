#!/usr/bin/env python3
"""Task 5: Email Draft Composer — Layer 2a / CDP Page Tool with Verification
"""
import asyncio
import os
import sys
import subprocess
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from computer.skill import ComputerSkill
from schemas import NodeSpec

async def main():
    # 1. Launch Chrome with remote debugging port 9224
    print("Launching Google Chrome on port 9224...")
    subprocess.Popen([
        "google-chrome",
        "--remote-debugging-port=9224",
        "--new-window",
        "http://localhost:8110/static/email_draft.html"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(3.0)

    # 2. Setup task node with custom port in metadata
    node = NodeSpec(
        skill="computer",
        inputs=["USER_QUERY"],
        metadata={
            "app": "Chrome",
            "goal": "Write draft to 'student@example.com', subject 'Session 10 Submission', body 'Everything works perfectly', click Save Draft, and verify saving",
            "cdp_port": "9224"
        }
    )

    # We need to tell our skill to use cdp_port 9224 if configured in metadata
    sk = ComputerSkill(
        artifacts_root=str(Path(__file__).resolve().parent / "state" / "task5_email"),
        session="task5_email_run",
    )

    # 3. Run the task
    print("Starting email draft composer agent...")
    res = await sk.run(node)
    
    print("\n" + "=" * 60)
    print("RESULT")
    print("=" * 60)
    print(f"  Success: {res.success}")
    print(f"  Path:    {res.output.get('path', '?')}")
    print(f"  Content: {res.output.get('content', '?')}")
    print(f"  Turns:   {res.output.get('turns', 0)}")
    
    # Cleanup Chrome
    subprocess.run(["killall", "chrome", "google-chrome"], capture_output=True)

if __name__ == "__main__":
    asyncio.run(main())
