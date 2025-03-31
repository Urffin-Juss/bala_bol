from bot import Bot
from dotenv import load_dotenv
import logging
import os

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main() -> None:
    load_dotenv()

    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("Токен не найден в переменных окружения. Проверьте файл .env")
        raise ValueError("Токен не найден в переменных окружения. Проверьте файл .env")

    logger.info("Запуск бота....")
    bot = Bot(token=token)
    bot.run()


if __name__ == '__main__':
    main()