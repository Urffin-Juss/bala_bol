from bot import Bot
from dotenv import load_dotenv
import logging
import os
import sys

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log')
    ]
)
logger = logging.getLogger(__name__)


def main() -> None:
    try:
        # Загрузка переменных окружения
        load_dotenv()

        # Получение токена
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not token:
            logger.error("Токен не найден. Проверьте:")
            logger.error("1. Существование файла .env")
            logger.error("2. Наличие TELEGRAM_BOT_TOKEN в .env")
            logger.error("3. Что файл .env в той же папке, что и main.py")
            raise ValueError("TELEGRAM_BOT_TOKEN не найден в переменных окружения")

        logger.info("Инициализация бота...")
        bot = Bot(token=token)

        logger.info("Бот запущен и ожидает сообщений...")
        bot.run()

    except Exception as e:
        logger.critical(f"Критическая ошибка: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()