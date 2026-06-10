import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "src" / "notebooklm_skill" / "cli.py"


def run_nlm(args, *, cwd, env=None, stdin=None):
    command = [sys.executable, str(CLI), *args]
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        command,
        cwd=cwd,
        input=stdin,
        text=True,
        capture_output=True,
        env=merged_env,
    )


def write_rc(path, notebook_id, notebook_name):
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "notebook_id": notebook_id,
                "notebook_name": notebook_name,
            }
        ),
        encoding="utf-8",
    )


def write_fake_notebooklm(home):
    bin_dir = home / ".local" / "share" / "notebooklm-skill" / ".venv" / "bin"
    bin_dir.mkdir(parents=True)
    log_path = home / "notebooklm-calls.log"
    fake = bin_dir / "notebooklm"
    fake.write_text(
        f"""#!/usr/bin/env python3
import json
import pathlib
import sys
log = pathlib.Path({str(log_path)!r})
log.write_text(log.read_text() + ' '.join(sys.argv[1:]) + '\\n' if log.exists() else ' '.join(sys.argv[1:]) + '\\n')
if sys.argv[1:] == ['list', '--json']:
    print(json.dumps({{'notebooks': [{{'id': 'nb-project', 'title': 'Project Notebook'}}], 'count': 1}}))
elif sys.argv[1:2] == ['ask']:
    print('answer from notebooklm')
sys.exit(0)
""",
        encoding="utf-8",
    )
    fake.chmod(0o755)
    return log_path


def test_which_resolves_project_binding_from_parent_directory(tmp_path):
    home = tmp_path / "home"
    workspace = home / "Documents" / "Information_Security"
    child = workspace / "week3" / "notes"
    child.mkdir(parents=True)
    write_rc(workspace / ".notebooklmrc", "nb-info-sec", "Information Security")

    env = {"HOME": str(home)}
    result = run_nlm(["which"], cwd=child, env=env)

    assert result.returncode == 0
    assert "notebook_id: nb-info-sec" in result.stdout
    assert "notebook_name: Information Security" in result.stdout
    assert "source_type: rc" in result.stdout
    assert f"source: {workspace / '.notebooklmrc'}" in result.stdout
    assert result.stderr == ""


def test_which_uses_longest_user_path_binding_when_no_project_binding_exists(tmp_path):
    home = tmp_path / "home"
    documents = home / "Documents"
    workspace = documents / "Information_Security"
    child = workspace / "week3" / "notes"
    state_dir = home / ".local" / "state" / "notebooklm-skill"
    child.mkdir(parents=True)
    state_dir.mkdir(parents=True)
    map_path = state_dir / "workspace-map.json"
    map_path.write_text(
        json.dumps(
            {
                "version": 1,
                "workspaces": {
                    str(documents): {
                        "notebook_id": "nb-docs",
                        "notebook_name": "Documents Default",
                    },
                    str(workspace): {
                        "notebook_id": "nb-info-sec",
                        "notebook_name": "Information Security",
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    env = {"HOME": str(home)}
    result = run_nlm(["which"], cwd=child, env=env)

    assert result.returncode == 0
    assert "notebook_id: nb-info-sec" in result.stdout
    assert "notebook_name: Information Security" in result.stdout
    assert "source_type: user" in result.stdout
    assert f"source: {map_path}" in result.stdout
    assert f"workspace: {workspace}" in result.stdout
    assert result.stderr == ""


def test_project_binding_takes_precedence_over_user_path_binding(tmp_path):
    home = tmp_path / "home"
    workspace = home / "Documents" / "Information_Security"
    child = workspace / "week3" / "notes"
    state_dir = home / ".local" / "state" / "notebooklm-skill"
    child.mkdir(parents=True)
    state_dir.mkdir(parents=True)
    write_rc(workspace / ".notebooklmrc", "nb-project", "Project Notebook")
    (state_dir / "workspace-map.json").write_text(
        json.dumps(
            {
                "version": 1,
                "workspaces": {
                    str(workspace): {
                        "notebook_id": "nb-user",
                        "notebook_name": "User Notebook",
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    env = {"HOME": str(home)}
    result = run_nlm(["which"], cwd=child, env=env)

    assert result.returncode == 0
    assert "notebook_id: nb-project" in result.stdout
    assert "notebook_name: Project Notebook" in result.stdout
    assert "source_type: rc" in result.stdout
    assert "nb-user" not in result.stdout
    assert result.stderr == ""


def test_ask_rejects_empty_question(tmp_path):
    home = tmp_path / "home"
    workspace = home / "Documents" / "Information_Security"
    workspace.mkdir(parents=True)
    write_rc(workspace / ".notebooklmrc", "nb-project", "Project Notebook")

    env = {"HOME": str(home)}
    result = run_nlm(["ask"], cwd=workspace, env=env, stdin="")

    assert result.returncode == 1
    assert result.stdout == ""
    assert "Question is empty." in result.stderr


def test_ask_delegates_to_notebooklm_runtime_and_outputs_answer_only(tmp_path):
    home = tmp_path / "home"
    workspace = home / "Documents" / "Information_Security"
    workspace.mkdir(parents=True)
    write_rc(workspace / ".notebooklmrc", "nb-project", "Project Notebook")
    log_path = write_fake_notebooklm(home)

    env = {"HOME": str(home)}
    result = run_nlm(["ask", "What matters?"], cwd=workspace, env=env)

    assert result.returncode == 0
    assert result.stdout == "answer from notebooklm\n"
    assert result.stderr == ""
    assert log_path.read_text(encoding='utf-8').splitlines() == [
        'ask --notebook nb-project What matters?',
    ]


def test_use_writes_project_binding_and_excludes_it_from_git(tmp_path):
    home = tmp_path / "home"
    workspace = home / "Documents" / "Information_Security"
    git_info = workspace / ".git" / "info"
    workspace.mkdir(parents=True)
    git_info.mkdir(parents=True)
    (git_info / "exclude").write_text("", encoding="utf-8")
    write_fake_notebooklm(home)

    env = {"HOME": str(home)}
    result = run_nlm(["use", "nb-project"], cwd=workspace, env=env)

    assert result.returncode == 0
    assert "Configured NotebookLM notebook for this workspace." in result.stdout
    assert "notebook_id: nb-project" in result.stdout
    assert "notebook_name: Project Notebook" in result.stdout
    assert f"source: {workspace / '.notebooklmrc'}" in result.stdout
    assert result.stderr == ""
    assert json.loads((workspace / ".notebooklmrc").read_text(encoding="utf-8")) == {
        "version": 1,
        "notebook_id": "nb-project",
        "notebook_name": "Project Notebook",
    }
    assert ".notebooklmrc" in (git_info / "exclude").read_text(encoding="utf-8")
