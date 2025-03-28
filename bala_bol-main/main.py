from bot import Bot
from dotenv import load_dotenv
import os
import requests
imoprt asyncio
from logger_service import logger


async def async_main() -> None:

    load_dotenv()

    
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        await logger.error("Токен не найден в переменных окружения. Проверьте файл .env")
        raise ValueError("Токен не найден в переменных окружения. Проверьте файл .env")

    
    await logger.info("Запуск бота....")
    bot = Bot(token=token)
    await bot.run()
def main() -> None:
    asyncio.run(async_main())


if __name__ == '__main__':
    main()