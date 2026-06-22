#!/usr/bin/env python3
"""Task 4: Canvas Target Game — Layer 3 Vision
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
    # 1. Launch Chrome pointing to our local static game
    print("Launching Google Chrome...")
    subprocess.Popen([
        "google-chrome",
        "--new-window",
        "http://localhost:8110/static/click_game.html"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(3.0)

    # 2. Setup task node
    node = NodeSpec(
        skill="computer",
        inputs=["USER_QUERY"],
        metadata={
            "app": "Chrome",
            "goal": "Using vision, click inside the green target circle with the red bullseye on the canvas",
            "force_path": "vision"
        }
    )

    sk = ComputerSkill(
        artifacts_root=str(Path(__file__).resolve().parent / "state" / "task4_game"),
        session="task4_game_run",
    )

    # 3. Run the task
    print("Starting visual click agent on Canvas Target Game...")
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
