from telegram import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import logging
from typing import Optional, Dict
from typing import List, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class QuoteDB:
    def __init__(self, db_file: str = "quotes.db"):
        self.conn = sqlite3.connect(db_file)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):

        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS quotes (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    user_name TEXT NOT NULL,
                    text TEXT NOT NULL,
                    is_approved BOOLEAN DEFAULT 0
                )
            """)
            self.conn.commit()
            logger.info("Таблицы базы данных успешно инициализированы")
        except Exception as e:
            logger.error(f"Ошибка создания таблиц: {e}")
            raise

    def add_quote(self, user_id: int, user_name: str, text: str) -> bool:

        try:
            cursor = self.conn.execute(
                "INSERT INTO quotes (user_id, user_name, text, is_approved) VALUES (?, ?, ?, 1)",
                (user_id, user_name, text.strip())
            )
            self.conn.commit()
            logger.info(f"Добавлена цитата ID={cursor.lastrowid}")
            return True
        except Exception as e:
            logger.error(f"Ошибка добавления цитаты: {e}")
            return False

    def get_random_quote(self) -> Optional[Dict]:

        try:
            cursor = self.conn.execute("""
                SELECT id, user_name, text 
                FROM quotes 
                WHERE is_approved = 1
                ORDER BY RANDOM() 
                LIMIT 1
            """)
            result = cursor.fetchone()
            return dict(result) if result else None
        except Exception as e:
            logger.error(f"Ошибка при получении цитаты: {e}")
            return None

    def debug_quotes(self):

        try:
            cursor = self.conn.execute("SELECT * FROM quotes")
            logger.debug("Содержимое таблицы quotes:")
            for row in cursor.fetchall():
                logger.debug(dict(row))
        except Exception as e:
            logger.error(f"Ошибка при отладке: {e}")


class Feedback:
    def __init__(self, form_url: str, admin_chat_id: Optional[int] = None):
        self.form_url = form_url
        self.admin_chat_id = admin_chat_id

    async def handle_feedback(self, update, context):

        try:
            await update.message.reply_text(
                "📝 Оставьте отзыв:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Открыть форму", url=self.form_url)]
                ])
            )
        except Exception as e:
            logger.error(f"Feedback error: {e}")
            await update.message.reply_text("⚠️ Ошибка при открытии формы")


class GossipDB:
    def __init__(self, path: str = "quotes.db"):
        self.path = path
        self._init()

    def _init(self):
        with sqlite3.connect(self.path) as con:
            con.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                user_id INTEGER,
                user_name TEXT,
                text TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL
            );
            """)
            con.execute("CREATE INDEX IF NOT EXISTS idx_chat_time ON chat_messages(chat_id, created_at);")

    def add_message(self, chat_id: int, user_id: Optional[int], user_name: str, text: str):
        if not text: return
        with sqlite3.connect(self.path) as con:
            con.execute(
                "INSERT INTO chat_messages (chat_id, user_id, user_name, text, created_at) VALUES (?, ?, ?, ?, ?)",
                (chat_id, user_id, user_name, text[:2000], datetime.utcnow().isoformat())
            )

    def get_recent(self, chat_id: int, hours: int = 12, limit: int = 300) -> List[Dict[str, Any]]:
        since = datetime.utcnow() - timedelta(hours=hours)
        with sqlite3.connect(self.path) as con:
            con.row_factory = sqlite3.Row
            rows = con.execute(
                "SELECT user_name, text, created_at FROM chat_messages "
                "WHERE chat_id=? AND created_at>=? ORDER BY id DESC LIMIT ?",
                (chat_id, since.isoformat(), limit)
            ).fetchall()
        return [dict(r) for r in rows]