import sqlite3
from typing import Optional, Dict

class QuoteDB:
    def __init__(self, db_file: str = "quotes.db"):
        self.conn = sqlite3.connect(db_file)
        self.conn.row_factory = sqlite3.Row  
        self._init_db()

    def _init_db(self):
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS quotes (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            user_name TEXT NOT NULL,
            text TEXT NOT NULL,
            is_approved BOOLEAN DEFAULT 0
        )""")
        self.conn.commit()

    def add_quote(self, user_id: int, user_name: str, text: str) -> bool:
        try:
            cursor = self.conn.execute(
                "INSERT INTO quotes (user_id, user_name, text, is_approved) VALUES (?, ?, ?, 1)",  # is_approved=1
                
            (user_id, user_name, text.strip())
        )
            self.conn.commit()
            print(f"DEBUG: Цитата добавлена, ID={cursor.lastrowid}")  # Логируем добавление
            return True
        except Exception as e:
            print(f"DEBUG: Ошибка при добавлении цитаты: {e}")
            return False

    def get_random_quote(self) -> Optional[Dict]:
    
        try:
        
            self.conn.row_factory = sqlite3.Row
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
    
        cursor = self.conn.execute("SELECT * FROM quotes")
        for row in cursor.fetchall():
            print(dict(row))    