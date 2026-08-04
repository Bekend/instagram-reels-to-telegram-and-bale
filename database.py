import sys
import sqlite3
import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

DB_PATH = os.path.join(os.path.dirname(__file__), "app.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reels_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reel_id TEXT UNIQUE,
                url TEXT NOT NULL,
                author TEXT,
                caption TEXT,
                thumbnail_url TEXT,
                video_url TEXT,
                status TEXT DEFAULT 'discovered',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sent_at TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                level TEXT DEFAULT 'INFO',
                message TEXT NOT NULL
            )
        """)
        
        # Known chats/groups table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS known_chats (
                chat_id TEXT PRIMARY KEY,
                title TEXT,
                platform TEXT DEFAULT 'bale',
                chat_type TEXT DEFAULT 'group',
                selected INTEGER DEFAULT 1,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS liked_reels (
                reel_id TEXT PRIMARY KEY,
                liked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        defaults = {
            "target_platform": "both", # 'bale', 'telegram', or 'both'
            "bale_bot_token": "2023616365:J9T89Cz1N7jkj1SKFXWKRrfEIugIjqPrt0w",
            "bale_chat_ids": "4909719495, 5677988653",
            "bale_last_update_id": "0",
            "telegram_bot_token": "6035665773:AAHWj0nhI-TN5YAZeIwf4_4BJjsVWde6IkI",
            "telegram_chat_ids": "369523412",
            "telegram_last_update_id": "0",
            "send_to_all_groups": "true",

            "instagram_username": "ajksdjasdklaskdl",
            "instagram_password": "Asaljoon82@@",
            "instagram_session_id": "41411171535%3Ak5M6WVHGrl8nsR%3A1%3AAYiDl7IiHWekC84-JB9ENlHkr4McEfLbCIwmJ1HBuw",

            "auto_send_enabled": "true",
            "filter_keywords": "",
            "min_likes": "0",
            "send_mode": "video_file",
            "send_delay_min_seconds": "45",
            "send_delay_max_seconds": "75",
            "sleep_schedule_enabled": "true",
            "sleep_start_hour": "3",
            "sleep_end_hour": "10",
            "burst_mode_state": "active",

            "burst_end_time": "",
            "rest_end_time": "",
            "burst_min_minutes": "30",
            "burst_max_minutes": "60",
            "rest_min_minutes": "60",
            "rest_max_minutes": "120"
        }
        
        for k, v in defaults.items():
            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
            
        conn.commit()

def get_settings() -> Dict[str, str]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM settings")
        rows = cursor.fetchall()
        return {row["key"]: row["value"] for row in rows}

def update_settings(settings: Dict[str, str]):
    with get_connection() as conn:
        cursor = conn.cursor()
        for k, v in settings.items():
            cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (k, str(v)))
        conn.commit()

def add_known_chat(chat_id: str, title: str, platform: str = "bale", chat_type: str = "group"):
    if not chat_id:
        return
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO known_chats (chat_id, title, platform, chat_type, last_seen)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(chat_id) DO UPDATE SET
                title = excluded.title,
                platform = excluded.platform,
                last_seen = CURRENT_TIMESTAMP
        """, (str(chat_id), title or f"Group {chat_id}", platform, chat_type))
        conn.commit()

def update_chat_selection(chat_id: str, selected: bool):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE known_chats SET selected = ? WHERE chat_id = ?", (1 if selected else 0, str(chat_id)))
        conn.commit()

def get_known_chats(platform: Optional[str] = None) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        if platform:
            cursor.execute("SELECT * FROM known_chats WHERE platform = ? ORDER BY last_seen DESC", (platform,))
        else:
            cursor.execute("SELECT * FROM known_chats ORDER BY last_seen DESC")
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

def is_reel_processed(reel_id: str) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM reels_history WHERE reel_id = ?", (reel_id,))
        return cursor.fetchone() is not None

def add_reel(reel_data: Dict[str, Any]) -> bool:
    if is_reel_processed(reel_data["reel_id"]):
        return False
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO reels_history (reel_id, url, author, caption, thumbnail_url, video_url, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            reel_data["reel_id"],
            reel_data.get("url", ""),
            reel_data.get("author", "Instagram User"),
            reel_data.get("caption", ""),
            reel_data.get("thumbnail_url", ""),
            reel_data.get("video_url", ""),
            reel_data.get("status", "discovered")
        ))
        conn.commit()
        return True

def is_reel_liked(reel_id: str) -> bool:
    """Checks if a reel has already been liked on Instagram."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM liked_reels WHERE reel_id = ?", (reel_id,))
        return cursor.fetchone() is not None

def mark_reel_as_liked(reel_id: str):
    """Marks a reel as liked in the database."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO liked_reels (reel_id) VALUES (?)", (reel_id,))
        conn.commit()

def clear_reels_history():

    """Wipes all past reels from the database stream."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM reels_history")
        conn.commit()

def mark_reel_status(reel_id: str, status: str):

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE reels_history 
            SET status = ?, sent_at = CASE WHEN ? = 'sent' THEN CURRENT_TIMESTAMP ELSE sent_at END 
            WHERE reel_id = ?
        """, (status, status, reel_id))
        conn.commit()

def get_reel_by_id(reel_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a specific reel from the database by its reel_id."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reels_history WHERE reel_id = ?", (reel_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_reels(limit: int = 50, status: Optional[str] = None) -> List[Dict[str, Any]]:

    with get_connection() as conn:
        cursor = conn.cursor()
        if status:
            cursor.execute("SELECT * FROM reels_history WHERE status = ? ORDER BY created_at DESC LIMIT ?", (status, limit))
        else:
            cursor.execute("SELECT * FROM reels_history ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

def add_log(message: str, level: str = "INFO"):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO logs (message, level) VALUES (?, ?)", (message, level))
        conn.commit()

def get_logs(limit: int = 100) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM logs ORDER BY id DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

if __name__ == "__main__":
    init_db()
    print("Database updated.")
