## Assignment

Build a Computer-Use skill that drops into the Session 9 catalogue and solves three real tasks on your primary OS. Respect the five-layer architecture so the cascade discipline is visible in the code. Record every run with start_recording and submit the trajectory directory as evidence.

Pick three tasks from this list:

1.A Calculator or simple-arithmetic task using deterministic hotkeys (Layer 2a).

2.A spreadsheet or notes-app task using the AX tree and cheap text LLM judgment (Layer 2b).

3.A task in an Electron app (VS Code, Slack, Cursor, Notion, Discord) using the page tool with electron_debugging_port.

4.A task in a canvas-rendered or game-style target that forces Layer 3 vision (a small browser game, Figma desktop, a sketching app with no ARIA).

5.An email or message draft composition that exercises Layer 2b with strong verification.

6.A multi-app workflow that switches between two apps and moves data between them.

**Constraints:**

  At least one task uses vision.

  At least one task uses the Electron page path.

  At least one task completes with zero vision calls.


**Submission:** a GitHub repository README and a YouTube demo. The README covers the architecture (the five layers), the three tasks, the cascade decisions, and any failure modes encountered. The YouTube demo shows the agent operating live for at least one task with the agent-cursor overlay visible.

**Constraints on the path**: no paid APIs, no third-party agentic frameworks. V9 gateway from Session 9 for all LLM and vision calls. cua-driver as the substrate. Read CUA_DRIVER_GUIDE.md before starting.