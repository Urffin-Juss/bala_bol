import os
import logging
from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    filters,
    ContextTypes
)
from handlers import Handlers
from models import QuoteDB, Feedback

logger = logging.getLogger(__name__)

class Bot:
    def __init__(self, token: str):
        self.token = token
        self.db = QuoteDB(db_file="quotes.db")

        self.feedback = Feedback(
            form_url=os.getenv("FEEDBACK_FORM_URL"),
            admin_chat_id=int(os.getenv("ADMIN_CHAT_ID")) if os.getenv("ADMIN_CHAT_ID") else None
        )
        
        
        self.handlers = Handlers(db=self.db, feedback=self.feedback)

        self.app = Application.builder() \
            .token(self.token) \
            .build()

        self._setup_handlers()
        self._setup_error_handler()

    def _setup_handlers(self):

        handlers = [
            
            MessageHandler(
                filters.TEXT & filters.REPLY & filters.Regex(r'^цтт$'),
                self.handlers.add_quote_from_reply
            ),
            
            
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self.handlers.process_message
            ),
            
            # Можно добавить другие обработчики по необходимости
        ]
        
        for handler in handlers:
            self.app.add_handler(handler)

    def _setup_error_handler(self):

        async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
            logger.error(msg="Exception while handling update:", exc_info=context.error)

            if isinstance(update, Update):
                await update.message.reply_text("😢 Произошла ошибка. Попробуйте позже.")

        self.app.add_error_handler(error_handler)

    def run(self):

        try:
            logger.info("Starting bot...")
            self.app.run_polling()
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.critical(f"Fatal error: {e}")
            raise


if __name__ == "__main__":
    
    required_vars = {
        "TELEGRAM_BOT_TOKEN": "Токен бота",
        "FEEDBACK_FORM_URL": "Ссылка на форму обратной связи",
        "ADMIN_CHAT_ID": "ID чата админа (опционально)"
    }
    
    missing_vars = [name for name in required_vars if not os.getenv(name)]
    
    if missing_vars:
        logger.error(f"Отсутствуют обязательные переменные окружения: {', '.join(missing_vars)}")
        exit(1)
    
    try:
        Bot(os.getenv("TELEGRAM_BOT_TOKEN")).run()
    except Exception as e:
        logger.critical(f"Ошибка запуска бота: {e}")
        raise

