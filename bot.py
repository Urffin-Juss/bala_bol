from telegram.ext import Application, MessageHandler, filters
from telegram import Update
import os
from handlers import Handlers


class Bot:
    def __init__(self, token):
        self.token = token
        self.application = Application.builder().token(self.token).build()
        self.handlers = Handlers()

    def setup_handlers(self):
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handlers.handle_text)
        )

    def run(self):
        self.setup_handlers()
        print("Bot is activated... Knok-knok, Neo, the matrix has you")
        self.application.run_polling()


if __name__ == "__main__":
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set")
    bot = Bot(token)
    bot.run()