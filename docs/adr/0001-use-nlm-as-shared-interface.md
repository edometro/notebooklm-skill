# Use nlm as the shared NotebookLM interface

We will expose NotebookLM operations through an nlm CLI used by both humans and
Codex instead of asking users or agents to run long uv run notebooklm commands
directly. This keeps daily use short and predictable while giving the skill a
deterministic interface to call when it needs NotebookLM.

## Considered Options

- Keep NotebookLM operations as instructions in SKILL.md only.
- Add a shared nlm CLI and make the skill use it.

## Consequences

The skill becomes guidance for when to use NotebookLM, while repeated mechanics
such as workspace binding, config resolution, and command execution live in
code.
