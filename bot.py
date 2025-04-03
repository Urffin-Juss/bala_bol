from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from handlers import Handlers
from database import QuoteDB
import os
import logging

logger = logging.getLogger(__name__)

class Bot:
    def __init__(self, token):
        self.token = token
        self.db = QuoteDB()  
        self.handlers = Handlers(self.db)
        
        self.app = Application.builder() \
            .token(self.token) \
            .build()
        
        self._setup_handlers()
        self._setup_error_handler()

    def _setup_handlers(self):
        
        self.app.add_handler(
            MessageHandler(
                filters.TEXT & filters.REPLY & filters.Regex(r'^цтт$'),
                self.handlers._add_quote_from_reply
            )
        )
        
       
        self.app.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self.handlers.process_message
            )
        )
        
        

    def _setup_error_handler(self):
        
        async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
            logger.error(msg="Exception while handling update:", exc_info=context.error)
            
            if isinstance(update, Update):
                await update.message.reply_text("😢 Произошла ошибка. Попробуйте позже.")
        
        self.app.add_error_handler(error_handler)

    def run(self):
        
        try:
            self.app.run_polling()
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.critical(f"Fatal error: {e}")
            raise

if __name__ == "__main__":
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Не задан токен бота!")
        exit(1)
        
    Bot(token).run()