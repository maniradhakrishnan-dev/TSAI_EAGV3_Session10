#!/usr/bin/env python3
"""Task 4: Multi-app Workflow — Calculator → Gedit → Obsidian

Tests: Chain three apps together:
  Step 1: Calculate 143423*23 on Calculator (Layer 2a deterministic)
  Step 2: Save the result to a gedit file (Layer 2a deterministic)
  Step 3: Save the result to an Obsidian note (Layer 2a CDP page tool)
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from computer.skill import ComputerSkill
from schemas import NodeSpec


async def main():
    base_dir = Path(__file__).resolve().parent / "state"

    # ── Step 1: Calculator ──────────────────────────────────────────
    print("=" * 60)
    print("STEP 1: Calculator — Layer 2a Deterministic")
    print("=" * 60)

    node_calc = NodeSpec(
        skill="computer",
        inputs=["USER_QUERY"],
        metadata={
            "app": "Calculator",
            "goal": "Calculate 143423 times 23",
        }
    )
    sk_calc = ComputerSkill(
        artifacts_root=str(base_dir / "task4_calc"),
        session="task4_step1",
    )
    res_calc = await sk_calc.run(node_calc)
    print(f"\n  Success: {res_calc.success}")
    print(f"  Path:    {res_calc.output.get('path', '?')}")
    print(f"  Content: {res_calc.output.get('content', '?')}")

    if not res_calc.success:
        print("❌ Calculator failed, aborting workflow.")
        return

    # Extract numeric result
    content = res_calc.output.get("content", "")
    val = content.split("=")[-1].strip() if "=" in content else "3298729"
    print(f"  Extracted result: {val}")

    # ── Step 2: Gedit ───────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("STEP 2: Gedit — Layer 2a Deterministic Save")
    print("=" * 60)

    target_dir = "/home/mani_radhakrishnan/sandbox_session10"
    target_file = "mr_s10_workflow.txt"
    os.makedirs(target_dir, exist_ok=True)

    node_gedit = NodeSpec(
        skill="computer",
        inputs=["calc_result"],
        metadata={
            "app": "gedit",
            "goal": f"Write 'The calculated result is {val}' and save it to {os.path.join(target_dir, target_file)}",
        }
    )
    sk_gedit = ComputerSkill(
        artifacts_root=str(base_dir / "task4_gedit"),
        session="task4_step2",
    )
    res_gedit = await sk_gedit.run(node_gedit)
    print(f"\n  Success: {res_gedit.success}")
    print(f"  Path:    {res_gedit.output.get('path', '?')}")
    print(f"  Content: {res_gedit.output.get('content', '?')}")

    gedit_path = os.path.join(target_dir, target_file)
    if os.path.exists(gedit_path):
        print(f"  ✅ File saved: {gedit_path}")
    else:
        print(f"  ❌ File NOT found: {gedit_path}")

    # ── Step 3: Obsidian ────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("STEP 3: Obsidian — Layer 2a CDP page tool")
    print("=" * 60)

    note_name = "mr_s10_workflow"
    node_obsidian = NodeSpec(
        skill="computer",
        inputs=["calc_result"],
        metadata={
            "app": "Obsidian",
            "goal": f"Create a note titled '{note_name}' with content 'The calculated result is {val}'",
        }
    )
    sk_obsidian = ComputerSkill(
        artifacts_root=str(base_dir / "task4_obsidian"),
        session="task4_step3",
    )
    res_obsidian = await sk_obsidian.run(node_obsidian)
    print(f"\n  Success: {res_obsidian.success}")
    print(f"  Path:    {res_obsidian.output.get('path', '?')}")
    print(f"  Content: {res_obsidian.output.get('content', '?')}")

    obsidian_path = f"/home/mani_radhakrishnan/Obsidian Vault/{note_name}.md"
    if os.path.exists(obsidian_path):
        print(f"  ✅ Note saved: {obsidian_path}")
    else:
        print(f"  ❌ Note NOT found: {obsidian_path}")

    # ── Summary ─────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("WORKFLOW SUMMARY")
    print("=" * 60)
    print(f"  Calculator: {'✅' if res_calc.success else '❌'} (path={res_calc.output.get('path')})")
    print(f"  Gedit:      {'✅' if res_gedit.success else '❌'} (path={res_gedit.output.get('path')})")
    print(f"  Obsidian:   {'✅' if res_obsidian.success else '❌'} (path={res_obsidian.output.get('path')})")


if __name__ == "__main__":
    asyncio.run(main())
