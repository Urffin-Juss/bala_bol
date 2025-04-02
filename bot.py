from telegram import Update
from telegram.ext import Application, MessageHandler, filters
from handlers import Handlers
from database import QuoteDB
import os

class Bot:
    def __init__(self, token):
        self.token = token
        self.db = QuoteDB()  
        self.handlers = Handlers(self.db)  
        
        self.app = Application.builder() \
            .token(self.token) \
            .build()
        
        self._setup_handlers()

    def _setup_handlers(self):
    # Обработчик ответов с "цтт"
        self.app.add_handler(
            MessageHandler(
                filters.TEXT & filters.REPLY & filters.Regex(r'^цтт$'),
                self.handlers._add_quote_from_reply
            )
        )
    
    # Обработчик запроса случайной цитаты
        self.app.add_handler(
            MessageHandler(
                filters.Regex(r'^цтт$') & ~filters.REPLY,
                self.handlers.handle_quote_command
            )
        )
        
        
        self.app.add_handler(
            MessageHandler(
                filters.TEXT & filters.Regex(
                    r'(?i)(^|\s)(мудрость|мудростью|скажи мудрость|дай мудрость)'
                ),
                self.handlers.wisdom  # Исправлено на правильное название метода
            )
        )    
    
    # Общий обработчик текстовых сообщений
        self.app.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self.handlers.process_message
            )
        )
    def run(self):
        self.app.run_polling()
        
        


if __name__ == "__main__":
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Не задан токен бота!")
        exit(1)
        
    Bot(token).run()