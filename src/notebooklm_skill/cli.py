"""Minimal nlm CLI implementation."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO


@dataclass(frozen=True)
class Binding:
    notebook_id: str
    notebook_name: str
    source_type: str
    source: Path
    workspace: Path | None = None


class NlmError(Exception):
    pass


class ExternalCommandError(Exception):
    def __init__(self, result: subprocess.CompletedProcess[str]):
        self.result = result


def skill_root() -> Path:
    return Path(__file__).resolve().parents[2]


def skill_bin_nlm() -> Path:
    return skill_root() / 'bin' / 'nlm'


def same_file(left: Path, right: Path) -> bool:
    try:
        return left.samefile(right)
    except OSError:
        return False


def print_check(name: str, status: str, detail: str, stdout: TextIO) -> None:
    print(name + ': ' + status + ' - ' + detail, file=stdout)


def parse_binding_fields(data: object, path: Path) -> tuple[str, str]:
    if not isinstance(data, dict):
        raise NlmError(f"Invalid binding object in {path}.")
    try:
        notebook_id = data["notebook_id"]
        notebook_name = data["notebook_name"]
    except KeyError as exc:
        raise NlmError(f"Missing required field {exc.args[0]} in {path}.") from exc

    if not isinstance(notebook_id, str) or not notebook_id:
        raise NlmError(f"Invalid notebook_id in {path}.")
    if not isinstance(notebook_name, str) or not notebook_name:
        raise NlmError(f"Invalid notebook_name in {path}.")
    return notebook_id, notebook_name


def read_json_file(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise NlmError(f"Invalid JSON in {path}: {exc}") from exc


def validate_version(data: object, path: Path) -> dict:
    if not isinstance(data, dict):
        raise NlmError(f"Invalid JSON object in {path}.")
    if data.get("version") != 1:
        if "version" not in data:
            raise NlmError(f"Missing config version in {path}.")
        raise NlmError(f"Unsupported config version {data.get('version')} in {path}.")
    return data


def load_project_binding(path: Path) -> Binding:
    data = validate_version(read_json_file(path), path)
    notebook_id, notebook_name = parse_binding_fields(data, path)
    return Binding(
        notebook_id=notebook_id,
        notebook_name=notebook_name,
        source_type="rc",
        source=path,
    )


def is_ancestor_or_self(parent: Path, child: Path) -> bool:
    try:
        child.relative_to(parent)
    except ValueError:
        return False
    return True


def iter_ancestors_to_home(cwd: Path, home: Path):
    current = cwd.resolve()
    home = home.resolve()
    if not is_ancestor_or_self(home, current):
        return

    while True:
        yield current
        if current == home:
            return
        current = current.parent


def user_map_path(home: Path) -> Path:
    return home / ".local" / "state" / "notebooklm-skill" / "workspace-map.json"


def runtime_notebooklm_path(home: Path) -> Path:
    return home / ".local" / "share" / "notebooklm-skill" / ".venv" / "bin" / "notebooklm"


def require_runtime_command(home: Path) -> Path:
    notebooklm = runtime_notebooklm_path(home)
    if not notebooklm.is_file():
        raise NlmError(f"Runtime not ready: {notebooklm} not found.")
    return notebooklm


def load_user_path_binding(cwd: Path, home: Path) -> Binding | None:
    path = user_map_path(home)
    if not path.is_file():
        return None
    data = validate_version(read_json_file(path), path)
    workspaces = data.get("workspaces")
    if not isinstance(workspaces, dict):
        raise NlmError(f"Invalid workspaces object in {path}.")

    cwd = cwd.resolve()
    home = home.resolve()
    matches: list[tuple[Path, str, str]] = []
    for raw_workspace, raw_binding in workspaces.items():
        if not isinstance(raw_workspace, str):
            raise NlmError(f"Invalid workspace path in {path}.")
        workspace = Path(raw_workspace).resolve()
        if not is_ancestor_or_self(home, workspace):
            continue
        if is_ancestor_or_self(workspace, cwd):
            notebook_id, notebook_name = parse_binding_fields(raw_binding, path)
            matches.append((workspace, notebook_id, notebook_name))

    if not matches:
        return None
    workspace, notebook_id, notebook_name = max(matches, key=lambda item: len(item[0].parts))
    return Binding(
        notebook_id=notebook_id,
        notebook_name=notebook_name,
        source_type="user",
        source=path,
        workspace=workspace,
    )


def resolve_binding(cwd: Path, home: Path) -> Binding | None:
    for directory in iter_ancestors_to_home(cwd, home):
        rc_path = directory / ".notebooklmrc"
        if rc_path.is_file():
            return load_project_binding(rc_path)
    return load_user_path_binding(cwd, home)


def print_binding(binding: Binding, stdout: TextIO) -> None:
    print(f"notebook_id: {binding.notebook_id}", file=stdout)
    print(f"notebook_name: {binding.notebook_name}", file=stdout)
    print(f"source_type: {binding.source_type}", file=stdout)
    print(f"source: {binding.source}", file=stdout)
    if binding.workspace is not None:
        print(f"workspace: {binding.workspace}", file=stdout)


def atomic_write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as tmp:
        tmp.write(text)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = Path(tmp.name)
    os.replace(tmp_path, path)


def find_git_root(start: Path) -> Path | None:
    current = start.resolve()
    while True:
        if (current / ".git").is_dir():
            return current
        if current.parent == current:
            return None
        current = current.parent


def ensure_project_binding_excluded(target_dir: Path) -> None:
    git_root = find_git_root(target_dir)
    if git_root is None:
        return
    exclude = git_root / ".git" / "info" / "exclude"
    exclude.parent.mkdir(parents=True, exist_ok=True)
    existing = exclude.read_text(encoding="utf-8") if exclude.exists() else ""
    if ".notebooklmrc" in {line.strip() for line in existing.splitlines()}:
        return
    with exclude.open("a", encoding="utf-8") as file:
        if existing and not existing.endswith("\n"):
            file.write("\n")
        file.write("# Added by nlm\n.notebooklmrc\n")


def list_notebooks(notebooklm: Path) -> list[dict[str, object]]:
    result = subprocess.run([str(notebooklm), 'list', '--json'], text=True, capture_output=True)
    if result.returncode != 0:
        raise ExternalCommandError(result)
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise NlmError('Could not parse notebooklm list --json output as JSON.') from exc
    if not isinstance(data, dict):
        raise NlmError('Could not parse notebooklm list --json output as an object.')
    notebooks = data.get('notebooks')
    if not isinstance(notebooks, list):
        raise NlmError('Could not parse notebooklm list --json notebooks as a list.')
    return [item for item in notebooks if isinstance(item, dict)]


def find_notebook(notebooklm: Path, notebook_id: str) -> tuple[str, str]:
    for item in list_notebooks(notebooklm):
        item_id = item.get('id')
        item_title = item.get('title')
        if item_id == notebook_id and isinstance(item_title, str) and item_title:
            return notebook_id, item_title
    raise NlmError(f'NotebookLM notebook not found: {notebook_id}')


def read_question(args: argparse.Namespace, stdin: TextIO) -> str:
    if args.question:
        return " ".join(args.question).strip()
    return stdin.read().strip()


def command_which(args: argparse.Namespace, stdout: TextIO, stderr: TextIO) -> int:
    home = Path(os.environ.get("HOME", str(Path.home())))
    binding = resolve_binding(Path.cwd(), home)
    if binding is None:
        print("No NotebookLM binding found for this workspace.", file=stderr)
        return 1
    print_binding(binding, stdout)
    return 0


def command_ask(args: argparse.Namespace, stdin: TextIO, stdout: TextIO, stderr: TextIO) -> int:
    question = read_question(args, stdin)
    if not question:
        print("Question is empty.", file=stderr)
        return 1

    home = Path(os.environ.get("HOME", str(Path.home())))
    binding = resolve_binding(Path.cwd(), home)
    if binding is None:
        print("No NotebookLM binding found for this workspace.", file=stderr)
        return 1

    notebooklm = require_runtime_command(home)
    ask_result = subprocess.run(
        [str(notebooklm), 'ask', '--notebook', binding.notebook_id, question],
        stdout=stdout,
        stderr=stderr,
    )
    return ask_result.returncode


def target_directory_for_use(args: argparse.Namespace) -> Path:
    if args.path is not None:
        target = Path(args.path)
        if not target.is_absolute():
            target = Path.cwd() / target
        target = target.resolve()
        if not target.is_dir():
            raise NlmError(f"--path must point to an existing directory: {target}")
        return target
    if args.git_root:
        git_root = find_git_root(Path.cwd())
        if git_root is None:
            raise NlmError("Git root not found for --git-root.")
        return git_root
    return Path.cwd().resolve()


def command_use(args: argparse.Namespace, stdout: TextIO, stderr: TextIO) -> int:
    home = Path(os.environ.get("HOME", str(Path.home())))
    notebooklm = require_runtime_command(home)
    notebook_id, notebook_name = find_notebook(notebooklm, args.notebook_id)
    target_dir = target_directory_for_use(args)
    data = {"version": 1, "notebook_id": notebook_id, "notebook_name": notebook_name}

    if args.user:
        path = user_map_path(home)
        if path.exists():
            map_data = validate_version(read_json_file(path), path)
        else:
            map_data = {"version": 1, "workspaces": {}}
        workspaces = map_data.setdefault("workspaces", {})
        if not isinstance(workspaces, dict):
            raise NlmError(f"Invalid workspaces object in {path}.")
        workspaces[str(target_dir)] = {"notebook_id": notebook_id, "notebook_name": notebook_name}
        atomic_write_json(path, map_data)
        binding = Binding(notebook_id, notebook_name, "user", path, target_dir)
    else:
        path = target_dir / ".notebooklmrc"
        atomic_write_json(path, data)
        ensure_project_binding_excluded(target_dir)
        binding = Binding(notebook_id, notebook_name, "rc", path)

    print("Configured NotebookLM notebook for this workspace.", file=stdout)
    print_binding(binding, stdout)
    return 0


def command_doctor(args: argparse.Namespace, stdout: TextIO, stderr: TextIO) -> int:
    home = Path(os.environ.get("HOME", str(Path.home())))
    ok = True

    print('nlm doctor', file=stdout)
    print_check('skill', 'ok', str(skill_root()), stdout)

    expected_nlm = skill_bin_nlm()
    path_nlm = shutil.which('nlm')
    if path_nlm is None:
        print_check('path', 'fail', 'nlm not found on PATH', stdout)
        ok = False
    else:
        path_nlm_path = Path(path_nlm).resolve()
        shim_text = path_nlm_path.read_text(encoding='utf-8', errors='ignore') if path_nlm_path.is_file() else ''
        if same_file(path_nlm_path, expected_nlm):
            print_check('path', 'ok', str(path_nlm_path), stdout)
        elif str(skill_root()) in shim_text and 'bin/nlm' in shim_text:
            print_check('path', 'ok', str(path_nlm_path) + ' delegates to ' + str(expected_nlm), stdout)
        else:
            print_check('path', 'fail', str(path_nlm_path) + ' does not point to ' + str(expected_nlm), stdout)
            ok = False

    notebooklm = runtime_notebooklm_path(home)
    if notebooklm.is_file():
        print_check('runtime', 'ok', str(notebooklm), stdout)
        result = subprocess.run([str(notebooklm), 'doctor'], text=True, capture_output=True)
        if result.returncode == 0:
            print_check('runtime doctor', 'ok', 'notebooklm doctor passed', stdout)
        else:
            print_check('runtime doctor', 'fail', 'notebooklm doctor failed', stdout)
            if result.stdout:
                print(result.stdout, end="", file=stdout)
            if result.stderr:
                print(result.stderr, end="", file=stderr)
            ok = False
    else:
        print_check('runtime', 'fail', str(notebooklm) + ' not found', stdout)
        ok = False

    try:
        binding = resolve_binding(Path.cwd(), home)
    except NlmError as exc:
        print_check('binding', 'fail', str(exc), stdout)
        ok = False
    else:
        if binding is None:
            print_check('binding', 'warn', 'No NotebookLM binding found for this workspace.', stdout)
        else:
            print_check('binding', 'ok', binding.notebook_name + ' (' + binding.notebook_id + ')', stdout)
            print_binding(binding, stdout)

    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nlm")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("which")
    subparsers.add_parser("doctor")
    ask_parser = subparsers.add_parser("ask")
    ask_parser.add_argument("question", nargs="*")
    use_parser = subparsers.add_parser("use")
    use_parser.add_argument("notebook_id")
    use_parser.add_argument("--git-root", action="store_true")
    use_parser.add_argument("--user", action="store_true")
    use_parser.add_argument("--path")
    return parser


def main(
    argv: list[str] | None = None,
    stdin: TextIO = sys.stdin,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "which":
            return command_which(args, stdout, stderr)
        if args.command == "doctor":
            return command_doctor(args, stdout, stderr)
        if args.command == "ask":
            return command_ask(args, stdin, stdout, stderr)
        if args.command == "use":
            return command_use(args, stdout, stderr)
    except ExternalCommandError as exc:
        if exc.result.stdout:
            print(exc.result.stdout, end="", file=stdout)
        if exc.result.stderr:
            print(exc.result.stderr, end="", file=stderr)
        return exc.result.returncode
    except NlmError as exc:
        print(str(exc), file=stderr)
        return 1
    parser.error(f"unknown command {args.command}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
