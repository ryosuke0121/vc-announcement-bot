# VC Announcement Bot

Discord ボイスチャンネルの通話開始/終了を自動で通知するBotです。

## 主な機能

- VC通話開始時の自動通知
- VC通話終了時の自動通知と通話時間・参加者表示
- ロールメンション機能
- 二重送信防止機能
- 参加者の記録とメンション表示

## 必要要件

- Docker
- Docker Compose
- Discord Bot Token

## セットアップ

### 1. リポジトリのクローン

```bash
git clone https://github.com/ryosuke0121/vc-announcement-bot.git
cd vc-announcement-bot
```

### 2. 環境変数の設定

`.env.example`をコピーして`.env`ファイルを作成し、Discord Bot Tokenを設定します。

```bash
cp .env.example .env
```

`.env`ファイルを編集:

```
DISCORD_BOT_TOKEN=your_bot_token_here
```

### 3. Discord Bot Tokenの取得方法

1. [Discord Developer Portal](https://discord.com/developers/applications)にアクセス
2. 「New Application」をクリックして新しいアプリケーションを作成
3. 左側メニューから「Bot」を選択
4. 「Add Bot」をクリック
5. 「TOKEN」セクションで「Reset Token」をクリックしてトークンを取得
6. 必要な権限 (Privileged Gateway Intents):
   - SERVER MEMBERS INTENT
   - PRESENCE INTENT (オプション)
   - MESSAGE CONTENT INTENT (オプション)

### 4. Botの招待

以下のURLでBotをサーバーに招待してください（CLIENT_IDは自分のBotのIDに置き換えてください）:

```
https://discord.com/oauth2/authorize?client_id=CLIENT_ID&permissions=2048&scope=bot%20applications.commands
```

必要な権限:
- View Channels
- Send Messages
- Embed Links
- Read Message History
- Use Slash Commands

### 5. 起動

```bash
docker-compose up -d
```

### 6. ログの確認

```bash
docker-compose logs -f
```

## 使い方

### スラッシュコマンド

#### `/monitor_setup`

VC通知設定を追加・更新します。

- `vc_channel`: 通知するボイスチャンネル
- `notification_channel`: 通知を送るテキストチャンネル
- `mention_role`: メンションするロール

管理者権限が必要です。

#### `/monitor_delete`

VC通知設定を削除します。

- `vc_channel`: 通知を解除するボイスチャンネル

管理者権限が必要です。

#### `/show_config`

現在の通知設定を表示します。

#### `/info`

Bot情報を表示します。

## 通知の仕組み

### 通話開始時

- 誰かがVCに参加すると10秒待機
- 10秒後にまだ誰かがVCにいる場合、通知を送信
- 設定されたロールにメンション

### 通話終了時

- 最後の人がVCから退出すると1秒待機
- 通話時間と参加者リストを含む通知を送信
- 参加者はメンション形式で表示

## データベース構造

SQLiteデータベースを使用しています。

### テーブル

- `guild_configs`: サーバーごとのVC通知設定
- `vc_states`: VC通話の状態管理
- `vc_participants`: 通話参加者の記録

## 開発

### ローカル環境での実行

```bash
# 依存関係のインストール
pip install -r requirements.txt

# データベースの初期化
python -c "import database; database.init_db()"

# Botの起動
python main.py
```

### 環境

- Python 3.11
- discord.py 2.3.2
- python-dotenv

## ライセンス

MIT License

## 作者

ryosuke0121

## バージョン履歴

- v2.0.0 (2025-12-24)
  - 通話終了時に参加者リストを表示
  - 参加者のメンション機能追加
  - データベースに参加者記録テーブル追加
  - 二重送信防止機能の強化
