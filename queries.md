# CLI Execution Queries for flow.py

To run these queries, navigate to the code directory first:
```bash
cd S9SharedCode/code
```

---

### 1. Calculator (Deterministic)
Runs the task using deterministic programmatic element matching (no LLM, 100% reliable).
```bash
uv run flow.py "calculate 234*567 using calculator app"
```

### 2. Calculator (Vision)
Forces the VLM vision-action loop to visually identify and click calculator buttons.
```bash
uv run flow.py "using vision, calculate 7 times 8 on the calculator"
```

### 3. Gedit (Text Editor)
Opens Gedit, writes the content, saves the file to the specified path, and closes Gedit.
```bash
uv run flow.py "Write 'Hello from Session 10' in gedit, save it to /home/mani_radhakrishnan/sandbox_session10/hello.txt, and close the app"
```

### 4. Obsidian (Markdown Notes)
Launches Obsidian, opens or creates the note, and appends/modifies text.
```bash
uv run flow.py "Open Obsidian, search for note 'mr_s10_workflow', and append the text 'Done!'"
```

### 5. Sliding Puzzle (Vision Canvas)
Loads the HTML puzzle in Chrome, visually locates the misplaced tile using the VLM, and clicks it to solve the grid.
```bash
uv run flow.py "Using vision, identify the numbered tile that is out of order on the sliding puzzle grid, click it to restore order (1-8 with the empty slot in the bottom-right), and verify that the status says Solved"
```

### 6. Email Draft (Browser-based)
Launches Chrome, goes to the webmail interface (or generic mail app), and drafts the specified email.
```bash
uv run flow.py "Draft an email to mani@example.com with subject 'Workflow Complete' and body 'The multi-app execution finished successfully.'"
```

### 7. Multi-App Workflow
Computes the arithmetic calculation, saves the resulting output text file using Gedit, and appends the result into your Obsidian vault:
```bash
uv run flow.py "Calculate 143423 times 23, save it to a gedit file at /home/mani_radhakrishnan/sandbox_session10/mr_s10_workflow.txt, and create an Obsidian note with the result"
```
