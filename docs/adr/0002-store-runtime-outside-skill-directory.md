# Store the NotebookLM runtime outside the skill directory

We will store the NotebookLM runtime under ~/.local/share/notebooklm-skill
instead of inside the skill directory. The skill can be installed globally or
checked out as a workspace-local submodule, so keeping one user-level runtime
avoids creating separate virtual environments for each copy of the skill.

## Considered Options

- Put .venv inside each skill checkout.
- Use one user-level runtime under ~/.local/share/notebooklm-skill.

## Consequences

The executable and skill files can move independently from the runtime. Runtime
setup and version checks must therefore be explicit instead of relying on a
.venv beside the skill files.
