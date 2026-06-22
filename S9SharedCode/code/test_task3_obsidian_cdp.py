#!/usr/bin/env python3
"""Task 3: Obsidian — Electron CDP page tool

Tests: Save a note to Obsidian via the CDP page tool (execute_javascript).
Expected: Layer 2a launches Obsidian with --remote-debugging-port=9222,
          uses the page tool to call app.vault.create(), verifies file on disk.
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from computer.skill import ComputerSkill
from schemas import NodeSpec


async def main():
    obsidian_vault = "/home/mani_radhakrishnan/Obsidian Vault"
    note_name = "mr_s10_result"

    node = NodeSpec(
        skill="computer",
        inputs=["USER_QUERY"],
        metadata={
            "app": "Obsidian",
            "goal": f"Create a note titled '{note_name}' with content 'The calculated result is 3298729' in Obsidian",
        }
    )
    sk = ComputerSkill(
        artifacts_root=str(Path(__file__).resolve().parent / "state" / "task3_obsidian_cdp"),
        session="task3_obsidian_cdp",
    )
    print("=" * 60)
    print("TASK 3: Obsidian — Electron CDP page tool")
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
    target_path = os.path.join(obsidian_vault, f"{note_name}.md")
    if os.path.exists(target_path):
        with open(target_path) as f:
            content = f.read().strip()
        print(f"✅ PASS: Note saved at {target_path}")
        print(f"   Content: {content!r}")
    else:
        print(f"❌ FAIL: Note not found at {target_path}")


if __name__ == "__main__":
    asyncio.run(main())
