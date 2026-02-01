import sqlite3
import os

DB_FILE = "data/bot.db"

def get_connection():
    """データベース接続を取得する"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """データベースとテーブルを初期化する"""
    conn = get_connection()
    c = conn.cursor()
    # guild_configs テーブル作成
    # guild_id をプライマリキーの一部にするか、ユニーク制約をつける
    # 1つのサーバーで複数のVC設定を持ちたい場合は、(guild_id, vc_id) をユニークにする
    c.execute('''
        CREATE TABLE IF NOT EXISTS guild_configs (
            guild_id INTEGER NOT NULL,
            vc_id INTEGER NOT NULL,
            notification_channel_id INTEGER NOT NULL,
            role_id INTEGER,
            PRIMARY KEY (guild_id, vc_id)
        )
    ''')
    
    # vc_states テーブル作成 (通話状態を永続化)
    c.execute('''
        CREATE TABLE IF NOT EXISTS vc_states (
            guild_id INTEGER NOT NULL,
            vc_id INTEGER NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 0,
            start_time TEXT,
            notification_message_id INTEGER,
            PRIMARY KEY (guild_id, vc_id)
        )
    ''')
    
    # vc_participants テーブル作成 (通話参加者を記録)
    c.execute('''
        CREATE TABLE IF NOT EXISTS vc_participants (
            guild_id INTEGER NOT NULL,
            vc_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            user_name TEXT NOT NULL,
            PRIMARY KEY (guild_id, vc_id, user_id)
        )
    ''')
    
    conn.commit()
    conn.close()

def upsert_config(guild_id: int, vc_id: int, notification_channel_id: int, role_id: int = None):
    """設定を保存または更新する"""
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO guild_configs (guild_id, vc_id, notification_channel_id, role_id)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(guild_id, vc_id) DO UPDATE SET
            notification_channel_id = excluded.notification_channel_id,
            role_id = excluded.role_id
    ''', (guild_id, vc_id, notification_channel_id, role_id))
    conn.commit()
    conn.close()

def get_configs_by_guild(guild_id: int):
    """特定のサーバーの設定を全て取得する"""
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM guild_configs WHERE guild_id = ?', (guild_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_config(guild_id: int, vc_id: int):
    """特定のVCの設定を取得する"""
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM guild_configs WHERE guild_id = ? AND vc_id = ?', (guild_id, vc_id))
    row = c.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def get_all_configs():
    """全ての設定を取得する"""
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM guild_configs')
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]
    
def delete_config(guild_id: int, vc_id: int):
    """設定を削除する"""
    conn = get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM guild_configs WHERE guild_id = ? AND vc_id = ?', (guild_id, vc_id))
    conn.commit()
    conn.close()

# --- VC状態管理関数 ---

def get_vc_state(guild_id: int, vc_id: int):
    """VC状態を取得する"""
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM vc_states WHERE guild_id = ? AND vc_id = ?', (guild_id, vc_id))
    row = c.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def set_vc_active(guild_id: int, vc_id: int, start_time: str, message_id: int):
    """VC状態をアクティブにする (通話開始)"""
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO vc_states (guild_id, vc_id, is_active, start_time, notification_message_id)
        VALUES (?, ?, 1, ?, ?)
        ON CONFLICT(guild_id, vc_id) DO UPDATE SET
            is_active = 1,
            start_time = excluded.start_time,
            notification_message_id = excluded.notification_message_id
    ''', (guild_id, vc_id, start_time, message_id))
    conn.commit()
    conn.close()

def set_vc_inactive(guild_id: int, vc_id: int):
    """VC状態を非アクティブにする (通話終了)"""
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        UPDATE vc_states 
        SET is_active = 0, start_time = NULL, notification_message_id = NULL
        WHERE guild_id = ? AND vc_id = ?
    ''', (guild_id, vc_id))
    conn.commit()
    conn.close()

def is_vc_active(guild_id: int, vc_id: int) -> bool:
    """VC状態がアクティブかどうかを確認する"""
    state = get_vc_state(guild_id, vc_id)
    return state and state['is_active'] == 1

# --- VC参加者管理関数 ---

def add_participant(guild_id: int, vc_id: int, user_id: int, user_name: str):
    """参加者を追加する"""
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT OR IGNORE INTO vc_participants (guild_id, vc_id, user_id, user_name)
        VALUES (?, ?, ?, ?)
    ''', (guild_id, vc_id, user_id, user_name))
    conn.commit()
    conn.close()

def get_participants(guild_id: int, vc_id: int):
    """参加者一覧を取得する"""
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT user_id, user_name FROM vc_participants WHERE guild_id = ? AND vc_id = ?', (guild_id, vc_id))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def clear_participants(guild_id: int, vc_id: int):
    """参加者一覧をクリアする"""
    conn = get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM vc_participants WHERE guild_id = ? AND vc_id = ?', (guild_id, vc_id))
    conn.commit()
    conn.close()
