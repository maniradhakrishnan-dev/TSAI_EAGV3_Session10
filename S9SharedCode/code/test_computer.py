import asyncio
import sys
from pathlib import Path

# Add S9SharedCode/code/ to system path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from computer.skill import ComputerSkill
from schemas import NodeSpec

async def test():
    node = NodeSpec(
        skill="computer",
        inputs=["USER_QUERY"],
        metadata={"app": "TextEdit", "goal": "Write 'hello world' into the text editor."}
    )
    sk = ComputerSkill(
        artifacts_root=Path(__file__).resolve().parent / "state" / "test_computer"
    )
    res = await sk.run(node)
    print("Real loop result:")
    print("Success:", res.success)
    print("Output:", res.output)
    print("Error:", res.error)

if __name__ == "__main__":
    asyncio.run(test())
