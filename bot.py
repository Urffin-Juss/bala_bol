from telegram.ext import Application, MessageHandler, filters
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
        print("Бот запущен и готов к работе! 🚀")
        self.application.run_polling()


if __name__ == "__main__":
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Ошибка: Токен не найден! Создайте файл .env с TELEGRAM_BOT_TOKEN=ваш_токен")
        exit(1)

    bot = Bot(token)
    bot.run()