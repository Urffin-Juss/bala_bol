from bot import Bot
from dotenv import load_dotenv
import os
import asyncio
from logger_service import logger


async def async_main() -> None:

    try:

        load_dotenv()
        await logger.debug("Переменные окружения загружены")


        token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not token:
            error_msg = "Токен не найден в переменных окружения. Проверьте файл .env"
            await logger.critical(error_msg)
            raise ValueError(error_msg)

        await logger.info("Инициализация бота...")
        bot = Bot(token=token)

        await logger.info("Запуск бота в режиме polling...")
        await bot.run()

    except Exception as e:
        await logger.error(f"Критическая ошибка: {str(e)}", exc_info=True)
        raise


def main() -> None:

    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        await logger.warning("Бот остановлен пользователем (Ctrl+C)")
    except Exception as e:
        await logger.critical(f"Фатальная ошибка: {str(e)}", exc_info=True)
        raise


if __name__ == '__main__':
    main()