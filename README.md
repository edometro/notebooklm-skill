# notebooklm-skill

notebooklm-skill は、Google NotebookLM をコマンドラインからプログラム的に操作するためのAIエージェント向けパッケージ型操作スキルです。

---

## 現行の実行モデル

本スキルの現行仕様では、各プロジェクトに個別の NotebookLM 用 venv を作らず、ユーザー単位の共有 runtime を使います。

- 共有 runtime: `~/.local/share/notebooklm-skill`
- 通常操作: `nlm doctor`, `nlm use`, `nlm which`, `nlm ask`
- 設計判断: `docs/adr/0001-use-nlm-as-shared-interface.md`, `docs/adr/0002-store-runtime-outside-skill-directory.md`
- 実Runtime検証: `docs/runtime-verification.md`
- PATH とテスト方針: `docs/testing-policy.md`

## 概要と目的 (What it does)

本スキルは、非公式 Python ライブラリ notebooklm-py を自動制御することで、Google NotebookLM をバックエンドとした強力な自動処理ワークフローをエージェントに提供します。

主な目的は以下の通りです：
- **ドキュメントのポッドキャスト自動生成**: Web記事や講義ノート等の資料を自動アップロードし、音声解説（Audio Overview/MP3）を全自動生成してダウンロード。
- **資料に基づく高度なリサーチ・問合せ**: ノートブックに登録されたソース情報に基づいて、CLI から質問（ask）を実行し、情報を即時要約・抽出。
- **対話的な安全選択**: エージェントが独断で新規ノートブックを無駄に作成したり、関係のないノートブックにデータを上書きしたりしないよう、既存のリストをユーザーに提示してチャットで明示的な確認を取る安全対策手順がパッケージ化されています。

---

## 利用している技術・依存ライブラリ (Under the hood)

本スキルは、以下のオープンソース技術および公式/非公式ライブラリに全面的に依存して動作します。

1. **Astral uv** (高速な Python パッケージおよびプロジェクトマネージャー)
   - Python の仮想環境管理、高速な依存解決、およびパッケージの一貫した実行（uv run）を提供。
2. **notebooklm-py** (非公式 Google NotebookLM CLI ラッパー)
   - Google NotebookLM 内部の GraphQL / REST API への通信をカプセル化し、CLI コマンドラインのインターフェースを提供。
3. **Playwright for Python (Chromium)**
   - notebooklm-py のログインプロセスでバックグラウンドでの Chromium ブラウザ自動操縦および Google 認証セッション情報（Cookies）の安全なキャッシュ保存を担当。
4. **markitdown** (ドキュメントコンバーター - 本リポジトリ連携)
   - 講義資料PDFや各種オフィスドキュメントなどを、情報損失ゼロで美しく構造化された Markdown（LaTeX 数式や Markdown テーブル）に事前変換するために連動して使用されます。

---

## パッケージファイル構成

```text
notebooklm-skill/
├── SKILL.md       # AIエージェント用の詳細な行動指針・手順定義ファイル
├── README.md      # スキル機能および利用技術についての開発者用解説（本ファイル）
└── LICENSE        # MIT ライセンスファイル
```

---

## ライセンス

本スキルは MIT License のもとで公開・管理されています。
詳細はパッケージ内の LICENSE ファイルを参照してください。

---

## 免責事項 (Disclaimer)

本ツールは非公式のAPIおよびライブラリ（`notebooklm-py`）を利用して Google NotebookLM を自動操作します。本ツールの利用は自己責任で行ってください。
過度なリクエストによるアカウントの制限や、Google側の仕様変更に伴う動作不良について、作者は一切の責任を負いません。
