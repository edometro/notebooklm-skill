# NotebookLM Skill

This context defines the language used by the NotebookLM skill and the nlm CLI.
It focuses on workspace binding and runtime boundaries, not implementation
details.

## Language

**Notebook workspace**:
A directory tree that nlm binds to a NotebookLM notebook. It may be a Git
repository, a course folder, or any working directory.
_Avoid_: Git repo, project, skill directory

**Project binding**:
A notebook binding stored in a .notebooklmrc file inside a notebook workspace.
It is resolved by walking upward from the current directory to the user home
directory.
_Avoid_: Local config, repo config

**User path binding**:
A notebook binding stored in the user workspace-map.json, keyed by an absolute
resolved Linux path. It is used only when no project binding is found.
_Avoid_: Global config, user config

**Notebook runtime**:
The user-level Python environment that contains notebooklm-py and its
dependencies. It is shared by all copies of the skill.
_Avoid_: Skill venv, project venv

**Executable shim**:
The small command placed on the user PATH as nlm. It delegates to the
Git-managed implementation in the skill repository.
_Avoid_: CLI implementation, runtime
