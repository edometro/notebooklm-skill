from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath


@dataclass(frozen=True)
class Binding:
    notebook_id: str
    notebook_name: str


@dataclass
class PrototypeState:
    home: PurePosixPath = PurePosixPath("/home/edometro")
    cwd: PurePosixPath = PurePosixPath("/home/edometro/Documents/Information_Security/week3")
    project_bindings: dict[PurePosixPath, Binding] = field(default_factory=dict)
    user_path_bindings: dict[PurePosixPath, Binding] = field(default_factory=dict)


def normalize_path(value: str | PurePosixPath, *, base: PurePosixPath | None = None) -> PurePosixPath:
    path = PurePosixPath(value)
    if not path.is_absolute():
        if base is None:
            raise ValueError("relative path requires a base")
        path = base / path
    parts: list[str] = []
    for part in path.parts:
        if part in ("", "/", "."):
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)
    return PurePosixPath("/", *parts)


def is_ancestor_or_self(parent: PurePosixPath, child: PurePosixPath) -> bool:
    parent_parts = parent.parts
    child_parts = child.parts
    return len(parent_parts) <= len(child_parts) and child_parts[: len(parent_parts)] == parent_parts


def ancestors_from_cwd_to_home(cwd: PurePosixPath, home: PurePosixPath) -> list[PurePosixPath]:
    if not is_ancestor_or_self(home, cwd):
        return []
    current = cwd
    result: list[PurePosixPath] = []
    while True:
        result.append(current)
        if current == home:
            return result
        current = current.parent


def resolve_binding(state: PrototypeState) -> tuple[str, PurePosixPath, Binding] | None:
    for path in ancestors_from_cwd_to_home(state.cwd, state.home):
        binding = state.project_bindings.get(path)
        if binding is not None:
            return ("project", path, binding)

    matches = [
        (path, binding)
        for path, binding in state.user_path_bindings.items()
        if is_ancestor_or_self(state.home, path) and is_ancestor_or_self(path, state.cwd)
    ]
    if not matches:
        return None
    path, binding = max(matches, key=lambda item: len(item[0].parts))
    return ("user", path, binding)
