# Runtime verification

This document records the latest real-runtime verification for the ADR 0001 and
ADR 0002 design.

## Verified environment

- Skill checkout: `/home/edometro/.gemini/config/skills/notebooklm-skill`
- Verified skill commit: `49d374d Align nlm runtime calls with notebooklm CLI`
- Notebook runtime: `~/.local/share/notebooklm-skill`
- Runtime setup style: `uv init --bare` plus `uv add 'notebooklm-py[browser]'`
- NotebookLM CLI version: `notebooklm-py` runtime reported `NotebookLM CLI, version 0.7.1`
- Auth profile path: `~/.notebooklm/profiles/default/storage_state.json`

## Commands verified

Runtime setup:

```bash
mkdir -p ~/.local/share/notebooklm-skill
cd ~/.local/share/notebooklm-skill
uv init --bare
uv add 'notebooklm-py[browser]'
uv run playwright install chromium
uv run notebooklm --version
```

Runtime health and login:

```bash
cd ~/.local/share/notebooklm-skill
uv run notebooklm doctor --fix
uv run notebooklm login
uv run notebooklm doctor
```

The final `doctor` run reported authenticated state as passing.

Workspace binding and ask flow:

```bash
/home/edometro/.gemini/config/skills/notebooklm-skill/bin/nlm which
/home/edometro/.gemini/config/skills/notebooklm-skill/bin/nlm use f5b27e6d-c61b-406a-978f-aaf87fb67ec7
/home/edometro/.gemini/config/skills/notebooklm-skill/bin/nlm which
/home/edometro/.gemini/config/skills/notebooklm-skill/bin/nlm ask 'このノートブックのタイトルは何ですか？'
```

The pre-binding `which` failed as expected. `use` then bound the workspace to the
NotebookLM notebook titled `一週間で身につくC言語`, and `ask` returned a real
NotebookLM answer identifying that title.

## Implications

- ADR 0001 is validated: humans and agents can use `nlm` instead of long
  `uv run notebooklm ...` commands for workspace-bound questions.
- ADR 0002 is validated: the runtime can live outside the skill checkout and be
  shared by multiple skill copies.
- `nlm use` depends on authenticated NotebookLM access because it validates the
  notebook ID through the real runtime.
- The currently verified direct entry point is the skill checkout's `bin/nlm`.
  Environments should also verify the PATH shim with `command -v nlm`,
  `nlm which`, and `nlm ask ...` when the user-facing command is expected to work.
