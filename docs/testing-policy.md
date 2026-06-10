# nlm path and testing policy

This document defines how to verify `nlm` without hiding PATH or runtime setup
problems, and how to keep tests useful when the CLI evolves.

## PATH policy

Do not modify `PATH` during user-facing verification.

First verify the command exactly as the user would run it:

```bash
command -v nlm
nlm --help
```

If this fails, report that the PATH shim is missing or not visible in the
current shell. Do not make the check pass by temporarily exporting a PATH inside
the verification command.

It is still valid to call the skill checkout implementation directly for
implementation-level checks:

```bash
/path/to/notebooklm-skill/bin/nlm --help
```

Treat these as separate checks:

- User-facing verification: `command -v nlm`, then `nlm ...`
- Implementation verification: skill checkout `bin/nlm ...`

## Test boundaries

Tests should lock down behavior that belongs to this skill, not incidental
behavior from `notebooklm-py`, Playwright, or Google auth.

Stable behavior worth testing:

- `.notebooklmrc` is resolved by walking upward from cwd to HOME.
- `.notebooklmrc` takes precedence over `workspace-map.json`.
- `workspace-map.json` uses longest ancestor match.
- `nlm ask` uses the resolved notebook ID.
- `nlm ask` sends NotebookLM answers to stdout and diagnostics/errors to stderr.
- The NotebookLM runtime is under `~/.local/share/notebooklm-skill`, not inside a
  skill checkout.
- `nlm use` writes versioned binding data.

Avoid overfitting tests to unstable details:

- Full external error messages from `notebooklm-py`.
- Browser or auth implementation details.
- Exact formatting of NotebookLM titles beyond the fields `nlm` stores.
- Long command sequences when a single externally supported command expresses
  the required behavior.

## Runtime contract

The current external contract used by `nlm` is:

- `notebooklm list --json` returns an object containing a `notebooks` list.
- Notebook entries contain `id` and `title` fields.
- `notebooklm ask --notebook <id> <question>` asks against a specific notebook
  without changing a global current notebook.

If `notebooklm-py` changes this contract, update the adapter code and tests
together. A failing test in that situation is useful: it points at a real
runtime integration change rather than a random regression.

## Specification changes

When changing `nlm` behavior, update these together when applicable:

1. `src/notebooklm_skill/cli.py`
2. `tests/test_nlm_cli.py`
3. `SKILL.md`
4. `README.md`
5. `docs/runtime-verification.md` after a real runtime check
6. ADRs only when the design decision itself changes
