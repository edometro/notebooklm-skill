from __future__ import annotations

import json
from pathlib import PurePosixPath

from resolver import Binding, PrototypeState, normalize_path, resolve_binding

BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"
CLEAR = "\033[2J\033[H"


def binding_for(label: str) -> Binding:
    slug = label.strip().replace(" ", "-").lower() or "notebook"
    return Binding(notebook_id=f"id-{slug}", notebook_name=label.strip() or "Notebook")


def render(state: PrototypeState, message: str = "") -> None:
    resolved = resolve_binding(state)
    print(CLEAR, end="")
    print(f"{BOLD}nlm resolution prototype{RESET}")
    print(f"{DIM}Question: do project bindings and user path bindings resolve predictably?{RESET}")
    print()
    print(f"{BOLD}cwd{RESET}: {state.cwd}")
    print(f"{BOLD}home{RESET}: {state.home}")
    print()
    print(f"{BOLD}resolved binding{RESET}:")
    if resolved is None:
        print("  none")
    else:
        source_type, path, binding = resolved
        print(f"  source_type: {source_type}")
        print(f"  path: {path}")
        print(f"  notebook_id: {binding.notebook_id}")
        print(f"  notebook_name: {binding.notebook_name}")
    print()
    print(f"{BOLD}project bindings (.notebooklmrc){RESET}:")
    print(json.dumps({str(k): v.__dict__ for k, v in state.project_bindings.items()}, indent=2, sort_keys=True))
    print()
    print(f"{BOLD}user path bindings (workspace-map.json){RESET}:")
    print(json.dumps({str(k): v.__dict__ for k, v in state.user_path_bindings.items()}, indent=2, sort_keys=True))
    print()
    if message:
        print(f"{DIM}{message}{RESET}")
        print()
    print(f"{BOLD}commands{RESET}:")
    print("  c PATH          set cwd")
    print("  p PATH NAME     add project binding at PATH")
    print("  u PATH NAME     add user path binding at PATH")
    print("  dp PATH         delete project binding")
    print("  du PATH         delete user path binding")
    print("  q               quit")


def parse_path(raw: str, state: PrototypeState) -> PurePosixPath:
    return normalize_path(raw, base=state.cwd)


def main() -> None:
    state = PrototypeState()
    state.project_bindings[PurePosixPath("/home/edometro/Documents/Information_Security")] = binding_for("Information Security")
    state.user_path_bindings[PurePosixPath("/home/edometro/Documents")] = binding_for("Documents Default")
    message = "Seeded with a project binding that overrides a broader user path binding."

    while True:
        render(state, message)
        message = ""
        try:
            line = input("> ").strip()
        except EOFError:
            return
        if not line:
            continue
        if line == "q":
            return
        parts = line.split(maxsplit=2)
        command = parts[0]
        try:
            if command == "c" and len(parts) >= 2:
                state.cwd = parse_path(parts[1], state)
            elif command in {"p", "u"} and len(parts) == 3:
                path = parse_path(parts[1], state)
                binding = binding_for(parts[2])
                if command == "p":
                    state.project_bindings[path] = binding
                else:
                    state.user_path_bindings[path] = binding
            elif command == "dp" and len(parts) >= 2:
                state.project_bindings.pop(parse_path(parts[1], state), None)
            elif command == "du" and len(parts) >= 2:
                state.user_path_bindings.pop(parse_path(parts[1], state), None)
            else:
                message = "Unknown command or missing argument."
        except ValueError as exc:
            message = str(exc)


if __name__ == "__main__":
    main()
