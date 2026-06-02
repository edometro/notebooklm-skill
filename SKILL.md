---
name: notebooklm-skill
description: Automate Google NotebookLM operations using the notebooklm-py CLI tool. Trigger this skill whenever the user wants to convert documents, PDFs, or web links into a podcast (Audio Overview), create or manage notebooks, upload sources, ask questions based on uploaded materials, or perform research using NotebookLM, even if they do not explicitly mention "notebooklm-py" or "CLI".
---

# NotebookLM 操作スキル

本スキルは、非公式 Python ライブラリ notebooklm-py を用いて CLI から Google NotebookLM を全自動で操作し、資料の追加、チャット（質問）、ポッドキャスト（Audio Overview）をはじめとする多様なコンテンツの自動生成およびダウンロードを正確に行うためのエージェント向けガイドです。

本スキルでは、ゼロからの uv 環境構築、初期設定、そして uv run notebooklm ask による動作疎通確認とユーザーへの利用開始報告までの一連の流れを、破綻のない論理的な順序で完全にカバーしています。

---

## 前提条件

- **プロジェクトのディレクトリ**: ユーザーが現在作業対象としている任意のプロジェクトディレクトリ（または uv で初期化され notebooklm-py が追加されているプロジェクト配下）
- **コマンドの実行**: 全ての Python コマンドは uv run を経由して仮想環境内で実行します。
- **セッション情報**: ログイン認証セッションが ~/.notebooklm/storage_state.json に保存される必要があります。

---

## 動作ワークフロー手順

エージェントは、以下の標準ワークフローを順番に実行しなければなりません。

### PHASE 0: ゼロからの環境構築（uv インストール）
もし環境に uv がインストールされていない場合は、以下の手順でインストールを行います。

1. **uv のインストール**:
   - **macOS / Linux**:
     ```bash
     curl -LsSf https://astral.sh/uv/install.sh | sh
     ```
   - **macOS (Homebrew)**:
     ```bash
     brew install uv
     ```
   - **Windows (PowerShell)**:
     ```powershell
     powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
     ```
2. **インストールの確認**:
   ```bash
   uv --version
   ```

---

### PHASE 1: プロジェクトの初期設定とライブラリ導入
環境構築後、作業ディレクトリにおいて NotebookLM を使用するための初期セットアップを行います。

1. **プロジェクトの初期化**:
   作業対象のディレクトリに移動し、`uv init` を実行します。
   ```bash
   uv init
   ```
 2. **notebooklm-py パッケージの追加**:
   ブラウザ自動ログイン機能を有効にするため、オプション付きでパッケージを追加します。
   ```bash
   uv add "notebooklm-py[browser]"
   ```
3. **Playwright のセットアップ**:
   自動ブラウザ操作用の Chromium をインストールします。
   ```bash
   uv run playwright install chromium
   ```
   > [!IMPORTANT]
   > **Linux環境における注意点**  
   > Linux環境（各種サーバー環境や、新しく用意したLinuxデスクトップなど）では、Chromiumを動かすために必要なシステム共有ライブラリが不足している場合があります。もし Chromium の起動エラー（Host system is missing dependencies...）が発生した場合は、以下のコマンドを実行してシステム依存パッケージを追加インストールしてください。
   > ```bash
   > uv run playwright install-deps chromium
   > ```

---

### PHASE 2: 初期ログインと言語設定
環境とパッケージが整ったら、Googleアカウントでのログインと出力設定を行います。

1. **Google アカウントによるログイン**:
   ```bash
   uv run notebooklm login
   ```
   自動起動したブラウザ上で Google ログインを完了させ、NotebookLMのホームが表示されたら、ターミナルに戻り「Enter」を押してセッション情報（~/.notebooklm/storage_state.json）を保存します。
   
   > [!NOTE]
   > ヘッドレス環境（SSH先などブラウザが直接起動できない場合）は、別のPCで生成した ~/.notebooklm/storage_state.json をサーバーの同一パスにコピーして配置することでもログイン状態を共有可能です。

2. **出力言語を日本語に固定**:
   生成されるポッドキャストや質問の回答が英語になるのを防ぐため、明示的に日本語を設定します。
   ```bash
   uv run notebooklm language set ja
   ```

---

### PHASE 3: ノートブックの選択または作成（重要・必須プロセス）
ログインが完了したら、操作対象となるノートブックを決定します。エージェントは独断でノートブックを作成したり特定のIDを使い回したりしてはなりません。必ず以下の手順を踏んでください。

1. **既存ノートブック一覧の取得**:
   現在のアカウント内に存在するノートブックのリストを取得します。
   ```bash
   uv run notebooklm list
   ```
2. **ユーザーへのインタラクティブな問い合わせ**:
   取得したリストをユーザーに提示し、以下のいずれを行うかを**チャットで必ず問いかけて確認を取得してください。**
   - **選択肢A (既存の利用)**: 提示したリストの中から既存のノートブックを選択し、そのIDを使用する。
   - **選択肢B (新規の作成)**: 新しいノートブックを新規に作成する（この場合はノートブックの名称をユーザーに確認する）。
3. **ノートブックの使用設定**:
   - 新規作成した場合は、以下のコマンドで作成後に発行される ID を控えます。
     ```bash
     uv run notebooklm create "新規ノートブック名"
     ```
   - 決定したノートブックのID（UUID形式）を、以後の操作対象としてアクティブに設定します。
     ```bash
     uv run notebooklm use <ノートブックのUUID>
     ```

---

### PHASE 4: 資料（ソース）の追加と READY 状態の待機
ノートブックの指定が完了したら、ポッドキャストやチャットの対象となる資料（URLやファイル）を追加し、READY状態になるまでループ待機します。

1. **ソースの追加**:
   ```bash
   # ソースの追加 (WebのURLまたはローカルファイルパスを指定)
   uv run notebooklm source add "https://example.com/article"
   ```

2. **READY状態の監視**:
   追加直後はステータスが processing になっています。以下のコマンドを定期的に実行し、**全てのソースが ready に変わるまでループ待機**してください。
   ```bash
   uv run notebooklm source list
   ```

---

### PHASE 5: ask コマンドによる疎通テスト（ユーザーへの利用開始報告）
ノートブックの設定とソース資料の登録が完了し、ready 状態になって初めて ask コマンドが正常に実行可能になります。ここで疎通テストを行い、ユーザーへ完了を報告します。

1. **ask コマンドによる疎通テスト**:
   動作確認として、以下のように簡単な質問を投げて NotebookLM の応答を確認します。
   ```bash
   uv run notebooklm ask "こんにちは。このノートブックのソースについて簡単に要約してください。"
   ```

2. **ユーザーへの利用開始報告**:
   疎通確認に成功したら、エージェントは**必ず以下のメッセージテンプレートに基づき、初期設定およびソース登録がすべて完了して利用可能になった旨をユーザーに報告してください。**
   
   > **ご報告メッセージの定型テンプレート**
   > ```text
   > uv の環境構築、パッケージのセットアップ、ログインおよびノートブックとソース資料の登録がすべて正常に完了いたしました。
   > 
   > 動作確認として uv run notebooklm ask による接続疎通を行い、登録されたソースに基づいた正確な応答を確認しております。
   > 
   > これで、いつでも uv run notebooklm ask によって登録された資料に対する質問やリサーチを行う準備が完全に整いました。
   > ```

---

### PHASE 6: ポッドキャスト等コンテンツの生成とダウンロード
疎通確認が完了し、ユーザーへの報告を終えたら、必要に応じてポッドキャストやスライド、クイズ等の自動生成とダウンロードを実行します。

- **ポッドキャスト（Audio Overview）の自動生成**:
  音声の生成には通常10分〜15分程度要します。
  ```bash
  # 生成の開始と完了待機 (10〜15分ほど要します)
  uv run notebooklm generate audio --wait
  ```
- **ポッドキャストMP3のダウンロード**:
  ```bash
  # 手元にMP3ファイルとしてダウンロード
  uv run notebooklm download audio ./podcast.mp3
  ```

---

## トラブルシューティング

### 1. 音声生成コマンドがタイムアウトした場合
`Error: Task <ID> timed out after 300.0s` というエラーで待機が切れた場合でも、バックグラウンドでの非同期生成は動いています。以下のコマンドで処理ステータスを追跡し、completed になったらダウンロードを実行してください。

```bash
# 生成状況の確認
uv run notebooklm artifact list

# 特定タスクの処理状況を取得
uv run notebooklm artifact get <タスクID>
```

### 2. 生成回数制限に達した場合
無料ユーザーは1日3回までの生成制限があります。制限エラーが発生した場合は、ユーザーに制限に達した旨を伝え、翌日に再実行するか NotebookLM Plus の利用を提案してください。
