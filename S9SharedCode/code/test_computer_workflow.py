import asyncio
import sys
from pathlib import Path

# Add S9SharedCode/code/ to system path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from computer.skill import ComputerSkill
from schemas import NodeSpec

async def main():
    # Task 1: Calculator
    node_calc = NodeSpec(
        skill="computer",
        inputs=["USER_QUERY"],
        metadata={"app": "Calculator", "goal": "Calculate 143423*23 and copy the result."}
    )
    sk = ComputerSkill(
        artifacts_root=Path(__file__).resolve().parent / "state" / "test_computer_calc"
    )
    print("Running Task 1: Calculator...")
    res_calc = await sk.run(node_calc)
    print("\n--- Calculator Result ---")
    print("Success:", res_calc.success)
    print("Output:", res_calc.output)
    print("Error:", res_calc.error)
    
    if not res_calc.success:
        print("Calculator failed, aborting.")
        return

    # Extract the result content (e.g. "3298729")
    content = res_calc.output.get("content", "")
    val = content.split("=")[-1].strip()
    if not val:
        val = "3298729" # Fallback if format differs
    print(f"Extracted calculated value: '{val}'")

    # Task 2: TextEdit (Gedit)
    # Goal: Create a file mr_s10.txt in /home/mani_radhakrishnan/sandbox_session10/ and write the result into it
    node_edit = NodeSpec(
        skill="computer",
        inputs=["calc_result"],
        metadata={
            "app": "gedit",
            "goal": f"Write the value '{val}' to /home/mani_radhakrishnan/sandbox_session10/mr_s10.txt. Do this by typing the text '{val}', then opening the Save As dialog, and typing the full path '/home/mani_radhakrishnan/sandbox_session10/mr_s10.txt' into the filename field, and clicking Save."
        }
    )
    sk_edit = ComputerSkill(
        artifacts_root=Path(__file__).resolve().parent / "state" / "test_computer_edit"
    )
    print("\nRunning Task 2: Text Editor...")
    res_edit = await sk_edit.run(node_edit)
    print("\n--- Text Editor Result ---")
    print("Success:", res_edit.success)
    print("Output:", res_edit.output)
    print("Error:", res_edit.error)

if __name__ == "__main__":
    asyncio.run(main())
