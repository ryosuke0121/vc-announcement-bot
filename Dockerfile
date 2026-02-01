# ベースイメージ
FROM python:3.9-slim

# 作業ディレクトリ
WORKDIR /app

# 依存関係ファイルのコピー
COPY requirements.txt .

# 依存関係のインストール
RUN pip install --no-cache-dir -r requirements.txt

# ソースコードのコピー
COPY . .

# Botの起動
CMD ["python", "main.py"]
