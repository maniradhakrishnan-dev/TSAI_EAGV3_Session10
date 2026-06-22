#!/usr/bin/env python3
"""Task 4: Visual Breakout Game — Layer 3 Vision
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
    # 1. Launch Chrome pointing to our breakout game
    print("Launching Google Chrome...")
    subprocess.Popen([
        "google-chrome",
        "--new-window",
        "http://localhost:8110/static/breakout_game.html"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(3.0)

    # 2. Setup task node
    node = NodeSpec(
        skill="computer",
        inputs=["USER_QUERY"],
        metadata={
            "app": "Breakout",
            "goal": "Using vision, find the yellow puck on the canvas, click on the canvas directly below it to align the blue paddle, then click 'Launch / Step' and verify it says HIT",
            "force_path": "vision"
        }
    )

    sk = ComputerSkill(
        artifacts_root=str(Path(__file__).resolve().parent / "state" / "task4_breakout"),
        session="task4_breakout_run",
    )

    # 3. Run the task
    print("Starting visual breakout game agent...")
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
