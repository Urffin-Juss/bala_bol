from telegram import Update  # Добавлен импорт Update
from telegram.ext import Application, MessageHandler, filters
import os
import asyncio
from handlers import Handlers

class Bot:
    def __init__(self, token):
        self.token = token
        # Настройка таймаутов для стабильного подключения
        self.application = Application.builder() \
            .token(self.token) \
            .read_timeout(30) \
            .write_timeout(30) \
            .connect_timeout(30) \
            .pool_timeout(30) \
            .build()
        self.handlers = Handlers()
        self.MAX_MESSAGE_LENGTH = 200  # Максимальная длина сообщения для обработки

    async def safe_handler(self, update: Update, context):  # Добавлена аннотация типа
        """Обертка для безопасной обработки сообщений"""
        try:
            # Проверка на длинные сообщения
            if len(update.message.text) > self.MAX_MESSAGE_LENGTH:
                await update.message.reply_text("Сообщение слишком длинное, я не могу его обработать 😅")
                return
            
            # Проверка, обращается ли пользователь к боту
            if not self.handlers.is_message_for_bot(update.message.text):
                return
                
            await self.handlers.process_message(update, context)
            
        except Exception as e:
            print(f"Ошибка при обработке сообщения: {e}")
            try:
                await update.message.reply_text("Произошла ошибка при обработке сообщения 😕")
            except:
                pass  # Если не удалось отправить сообщение об ошибке

    def setup_handlers(self):
        # Обработчик текстовых сообщений с фильтром
        self.application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self.safe_handler
            )
        )

    def run(self):  
        self.setup_handlers()
        print("Бот запущен и готов к работе! 🚀")
        try:
            self.application.run_polling(
                drop_pending_updates=True,  
                allowed_updates=Update.ALL_TYPES  
            )
        except KeyboardInterrupt:
            print("\nБот остановлен пользователем")
        except Exception as e:
            print(f"Бот завершил работу с ошибкой: {e}")
        finally:
            print("Работа бота завершена")

if __name__ == "__main__":
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Ошибка: Токен не найден! Создайте файл .env с TELEGRAM_BOT_TOKEN=ваш_токен")
        exit(1)

    bot = Bot(token)
    bot.run()