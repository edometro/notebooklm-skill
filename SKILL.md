---
name: notebooklm-skill
description: Use Google NotebookLM from Codex through the shared nlm CLI. Trigger this skill when the user wants to bind a workspace to a NotebookLM notebook, ask questions against NotebookLM sources, manage NotebookLM runtime setup, upload or inspect NotebookLM sources, or generate NotebookLM artifacts such as Audio Overview.
---

# NotebookLM 操作スキル

このスキルは、NotebookLM を `nlm` CLI 経由で使うための手順を定義します。
人間も Codex も、通常は長い `uv run notebooklm ...` を直接打たず、作業ディレクトリに対応する NotebookLM ノートブックを `nlm` で解決して操作します。

## 現行アーキテクチャ

- 共有 runtime: `~/.local/share/notebooklm-skill`
- runtime venv: `~/.local/share/notebooklm-skill/.venv`
- NotebookLM auth: `~/.notebooklm/profiles/default/storage_state.json`
- user-facing command: `nlm`
- Git-managed implementation: skill checkout の `bin/nlm` と `src/notebooklm_skill/cli.py`
- project binding: workspace 内の `.notebooklmrc`
- user path binding: `~/.local/state/notebooklm-skill/workspace-map.json`

## Runtime セットアップ

`uv` がない場合は先に導入します。

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

共有 runtime を作成します。

```bash
mkdir -p ~/.local/share/notebooklm-skill
cd ~/.local/share/notebooklm-skill
uv init --bare
uv add 'notebooklm-py[browser]'
uv run playwright install chromium
uv run notebooklm --version
```

Linux で Playwright の依存ライブラリが不足する場合のみ、次を実行します。

```bash
uv run playwright install-deps chromium
```

## Login と health check

```bash
cd ~/.local/share/notebooklm-skill
uv run notebooklm doctor --fix
uv run notebooklm login
uv run notebooklm doctor
```

`doctor` で Auth が pass になってから、`nlm use` や `nlm ask` を実行します。
未ログインの場合、`nlm use` は NotebookLM の notebook ID 検証で失敗します。

## Workspace binding

現在の workspace に NotebookLM notebook ID を紐付けます。

```bash
nlm use <notebook-id>
```

Git root に保存したい場合:

```bash
nlm use <notebook-id> --git-root
```

user path binding として保存したい場合:

```bash
nlm use <notebook-id> --user
nlm use <notebook-id> --user --path /absolute/workspace/path
```

`nlm use` は NotebookLM runtime の `list --json` で ID を検証し、notebook title を binding に保存します。

## Resolution と確認

```bash
nlm which
```

解決順序:

1. cwd から HOME まで親方向に `.notebooklmrc` を探す
2. 見つからない場合、`workspace-map.json` の longest ancestor match を使う

`.notebooklmrc` は user path binding より優先されます。

## Ask

```bash
nlm ask '質問文'
```

`nlm ask` は解決済み notebook ID を使って、実 runtime の `notebooklm ask --notebook <id>` を呼びます。
標準出力には NotebookLM の回答だけを出し、診断やエラーは標準エラーに出します。

## Notebook selection rule

NotebookLM notebook を新規作成したり既存 notebook を選ぶ場合、エージェントはユーザーに確認します。
既存 notebook の候補確認には runtime を直接使って構いません。

```bash
cd ~/.local/share/notebooklm-skill
uv run notebooklm list --json
```

ユーザーが ID を選んだ後に `nlm use <notebook-id>` で workspace に保存します。

## Sources and artifacts

ソース追加、Audio Overview 生成、artifact download など、まだ `nlm` にない操作は共有 runtime の `notebooklm` を直接使います。

```bash
cd ~/.local/share/notebooklm-skill
uv run notebooklm source add 'https://example.com/article'
uv run notebooklm source list
uv run notebooklm generate audio --wait
uv run notebooklm download audio ./podcast.mp3
```

対象 notebook が必要な操作では、事前に `nlm which` で binding を確認し、必要に応じて notebook ID を runtime command に渡してください。

## Verified runtime

最新の実 runtime 検証結果は `docs/runtime-verification.md` を参照してください。
