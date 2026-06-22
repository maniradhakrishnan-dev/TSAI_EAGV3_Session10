#!/usr/bin/env python3
"""Task 1a: Calculator — Layer 2a Deterministic (ZERO vision calls, $0 LLM cost)

Tests: Calculate 143423*23 using element_index clicks on gnome-calculator.
Expected: Layer 2a handles the entire flow. Result = 3298729.
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
            "goal": "Calculate 143423 times 23",
        }
    )
    sk = ComputerSkill(
        artifacts_root=str(Path(__file__).resolve().parent / "state" / "task1a_calc_det"),
        session="task1a_calc_det",
    )
    print("=" * 60)
    print("TASK 1a: Calculator — Layer 2a Deterministic")
    print("=" * 60)
    res = await sk.run(node)
    print("\n--- Result ---")
    print(f"  Success: {res.success}")
    print(f"  Path:    {res.output.get('path', '?')}")
    print(f"  Content: {res.output.get('content', '?')}")
    print(f"  Turns:   {res.output.get('turns', '?')}")
    print(f"  Error:   {res.error}")
    print("=" * 60)
    expected = "3298729"
    content = res.output.get("content", "")
    if expected in content:
        print(f"✅ PASS: Found expected result {expected} in output")
    else:
        print(f"❌ FAIL: Expected {expected} in '{content}'")


if __name__ == "__main__":
    asyncio.run(main())
