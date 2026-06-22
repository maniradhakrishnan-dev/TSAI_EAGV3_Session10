#!/usr/bin/env python3
"""Task 2a: Gedit — Layer 2a Deterministic Save (uses Layer 2a + Ctrl+L)

Tests: Write text to gedit and save to /home/mani_radhakrishnan/sandbox_session10/mr_s10_03.txt
Expected: Layer 2a types content, opens Save As, uses Ctrl+L to navigate, saves.
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from computer.skill import ComputerSkill
from schemas import NodeSpec


async def main():
    target_dir = "/home/mani_radhakrishnan/sandbox_session10"
    target_file = "mr_s10_03.txt"
    target_path = os.path.join(target_dir, target_file)

    os.makedirs(target_dir, exist_ok=True)

    node = NodeSpec(
        skill="computer",
        inputs=["USER_QUERY"],
        metadata={
            "app": "gedit",
            "goal": f"Write 'The calculated result is 3298729' and save it to {target_path}",
        }
    )
    sk = ComputerSkill(
        artifacts_root=str(Path(__file__).resolve().parent / "state" / "task2a_gedit_save"),
        session="task2a_gedit_save",
    )
    print("=" * 60)
    print("TASK 2a: Gedit — Layer 2a Deterministic Save")
    print("=" * 60)
    res = await sk.run(node)
    print("\n--- Result ---")
    print(f"  Success: {res.success}")
    print(f"  Path:    {res.output.get('path', '?')}")
    print(f"  Content: {res.output.get('content', '?')}")
    print(f"  Turns:   {res.output.get('turns', '?')}")
    print(f"  Error:   {res.error}")
    print("=" * 60)

    # Verify file on disk
    if os.path.exists(target_path):
        with open(target_path) as f:
            content = f.read().strip()
        print(f"✅ PASS: File saved at {target_path}")
        print(f"   Content: {content!r}")
    else:
        print(f"❌ FAIL: File not found at {target_path}")


if __name__ == "__main__":
    asyncio.run(main())
