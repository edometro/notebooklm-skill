---
name: notebooklm-skill
description: Use Google NotebookLM from Codex through the shared nlm CLI. Trigger this skill when the user wants to bind a workspace to a NotebookLM notebook, ask questions against NotebookLM sources, manage NotebookLM runtime setup, upload or inspect NotebookLM sources, or generate NotebookLM artifacts such as Audio Overview.
---

# NotebookLM 操作スキル

このスキルは、NotebookLM を `nlm` CLI 経由で使うための手順を定義します。
`nlm` は作業ディレクトリから NotebookLM notebook の binding を解決し、共有 runtime の `notebooklm` CLI を呼び出します。

初回利用者でも迷わないように、まず入口の `nlm`、次に共有 runtime、最後に workspace binding の順で確認します。

## 構成

- skill checkout: この `SKILL.md`、`bin/nlm`、`src/notebooklm_skill/cli.py` を含む Git 管理ディレクトリ
- user-facing command: ユーザーが普段打つ `nlm`
- PATH shim: `~/.local/bin/nlm` など、user-facing command から skill checkout の `bin/nlm` へつなぐ入口
- shared runtime: `~/.local/share/notebooklm-skill`
- runtime command: `~/.local/share/notebooklm-skill/.venv/bin/notebooklm`
- auth profile: `~/.notebooklm/profiles/default/storage_state.json`
- project binding: workspace 内の `.notebooklmrc`
- user path binding: `~/.local/state/notebooklm-skill/workspace-map.json`

skill checkout と shared runtime は別物です。skill checkout 内に `.venv` を作らないでください。

## まず確認すること

既存環境では、最初に user-facing command をそのまま確認します。確認のために一時的に `PATH` を足してはいけません。

```bash
command -v nlm
nlm --help
nlm doctor
```

`nlm doctor` は PATH shim、shared runtime、NotebookLM auth、現在の binding をまとめて確認します。成功したら、作業ディレクトリで binding を確認します。

```bash
nlm which
```

結果に応じて進みます。

- `nlm` が見つからない: PATH shim のセットアップへ進む
- runtime が見つからない: shared runtime のセットアップへ進む
- runtime doctor が失敗する: login と health check へ進む
- auth error: login と health check へ進む
- binding がない: notebook selection と workspace binding へ進む
- binding がある: `nlm ask '質問文'` を実行できる

## 初回セットアップ

### 1. skill checkout を確認する

このスキルの Git checkout があることを確認します。場所は環境ごとに異なります。

```bash
git -C /path/to/notebooklm-skill log -1 --oneline
```

既存の checkout を使う場合は、必要に応じて更新します。

```bash
git -C /path/to/notebooklm-skill pull
```

### 2. PATH shim を用意する

`nlm` が見つからない場合だけ、永続的な入口を作ります。確認用に一時的な `export PATH=...` で済ませないでください。

```bash
mkdir -p ~/.local/bin
ln -sf /path/to/notebooklm-skill/bin/nlm ~/.local/bin/nlm
```

symlink の代わりに、`NLM_SKILL_DIR` を使って skill checkout の `bin/nlm` に委譲する wrapper shim でも構いません。`nlm doctor` は symlink と wrapper の両方を診断します。

`~/.local/bin` がログインシェルの PATH に入っていない場合は、ユーザーに確認してから永続設定に追加します。Linux ではまず `~/.profile` を候補にし、理由なく `.bashrc` を汚さないでください。追加後は新しい shell で確認します。

```bash
command -v nlm
nlm --help
nlm doctor
```

skill checkout の `bin/nlm` を直接呼ぶのは実装確認としては有効ですが、ユーザーが普段 `nlm` と打てることの確認とは分けて扱います。

### 3. uv を用意する

```bash
uv --version
```

見つからない場合は導入します。

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 4. shared runtime を作る

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

### 5. login と health check を行う

```bash
cd ~/.local/share/notebooklm-skill
uv run notebooklm doctor --fix
uv run notebooklm login
uv run notebooklm doctor
```

`doctor` で Auth が pass になってから、`nlm use` や `nlm ask` を実行します。
未ログインの場合、`nlm use` は NotebookLM の notebook ID 検証で失敗します。

## 通常ワークフロー

### 1. workspace の binding を確認する

```bash
nlm which
```

binding がある場合は、そのまま質問できます。

```bash
nlm ask '質問文'
```

### 2. notebook を選ぶ

binding がない場合は、既存 notebook を確認してユーザーに選ばせます。エージェントが独断で notebook を新規作成したり、関係ない ID を使い回したりしないでください。

```bash
cd ~/.local/share/notebooklm-skill
uv run notebooklm list --json
```

ユーザーが notebook ID を選んだら、workspace に保存します。

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

### 3. binding の解決規則を理解する

`nlm which` と `nlm ask` は次の順で binding を解決します。

1. cwd から HOME まで親方向に `.notebooklmrc` を探す
2. 見つからない場合、`workspace-map.json` の longest ancestor match を使う

`.notebooklmrc` は user path binding より優先されます。

### 4. 質問する

```bash
nlm ask '質問文'
```

`nlm ask` は解決済み notebook ID を使って、実 runtime の `notebooklm ask --notebook <id>` を呼びます。
標準出力には NotebookLM の回答だけを出し、診断やエラーは標準エラーに出します。

## Sources and artifacts

ソース追加、Audio Overview 生成、artifact download など、まだ `nlm` にない操作は shared runtime の `notebooklm` を直接使います。
事前に `nlm which` で対象 notebook を確認し、**必ず `--notebook <id>` オプションを指定して実行してください。指定しないと、前回使用した別のノートブックに対して操作が実行されてしまう危険があります。**

```bash
# 1. ターゲットのNotebook IDを確認・取得する
NOTEBOOK_ID=$(nlm which)

# 2. --notebook オプションを明示して実行する
cd ~/.local/share/notebooklm-skill
uv run notebooklm source add --notebook "$NOTEBOOK_ID" 'https://example.com/article'
uv run notebooklm source list --notebook "$NOTEBOOK_ID"
uv run notebooklm generate audio --wait --notebook "$NOTEBOOK_ID"
uv run notebooklm download audio ./podcast.mp3 --notebook "$NOTEBOOK_ID"
```

notebook の新規作成、既存 notebook の選択、source 追加、artifact 生成はユーザー確認を取ってから実行します。

## Failure handling

- `command -v nlm` が失敗した場合は PATH shim が見えていない問題として扱います。一時的な PATH 追加で確認を通さないでください。
- `nlm which` が失敗しただけなら、まず binding 未設定として扱います。runtime を作り直さないでください。
- `Runtime not ready` が出た場合だけ shared runtime のセットアップを確認します。
- `nlm doctor` が失敗した場合は、表示された `path`、`runtime`、`runtime doctor` の fail 行から対応する setup 手順へ戻ります。
- `nlm use` が auth error で失敗した場合は、`uv run notebooklm doctor` と `uv run notebooklm login` を実行します。
- `nlm ask` は回答だけを stdout に出す前提です。エラーや診断は stderr として扱います。

## Maintenance notes

- PATH とテスト方針は `docs/testing-policy.md` を参照してください。
- 最新の実 runtime 検証結果は `docs/runtime-verification.md` を参照してください。
- `nlm` の挙動を変える場合は、`src/notebooklm_skill/cli.py`、`tests/test_nlm_cli.py`、`SKILL.md` を一緒に確認してください。
