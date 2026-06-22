#!/usr/bin/env python3
"""Task 1b: Calculator — Layer 3 Vision (forces vision path)

Tests: Calculate 7 times 8 using screenshot + VLM clicks.
Expected: Layer 3 handles the flow via gnome-screenshot + V9 /v1/vision.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from computer.skill import ComputerSkill
from schemas import NodeSpec


async def main():
    node = NodeSpec(
        skill="computer",
        inputs=["USER_QUERY"],
        metadata={
            "app": "Calculator",
            "goal": "Using vision, calculate 7 times 8 on the calculator",
            "force_path": "vision",
        }
    )
    sk = ComputerSkill(
        artifacts_root=str(Path(__file__).resolve().parent / "state" / "task1b_calc_vision"),
        session="task1b_calc_vision",
    )
    print("=" * 60)
    print("TASK 1b: Calculator — Layer 3 Vision")
    print("=" * 60)
    res = await sk.run(node)
    print("\n--- Result ---")
    print(f"  Success: {res.success}")
    print(f"  Path:    {res.output.get('path', '?')}")
    print(f"  Content: {res.output.get('content', '?')}")
    print(f"  Turns:   {res.output.get('turns', '?')}")
    print(f"  Error:   {res.error}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
