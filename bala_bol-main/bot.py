from telegram.ext import Application, CommandHandler
from telegram   import Update
import os
from handlers import Handlers
from logger_service import logger


async def initialize(self):

    try:
        await logger.info("Создание экземпляра Application...")
        self.application = Application.builder().token(self.token).build()
        await self.setup_handlers()
    except Exception as e:
        await logger.critical(f"Ошибка инициализации бота: {e}", exc_info=True)
        raise


async def setup_handlers(self):

    handlers_info = [
        ("start", self.handlers.start, "Старт бота"),
        ("weather", self.handlers.weather, "Запрос погоды"),
        ("joke", self.handlers.joke, "Случайная шутка"),
        ("info", self.handlers.info, "Информация"),
        ("titles", self.handlers.assing_titles, "Розыгрыш ролей")
    ]

    for command, handler, desc in handlers_info:
        try:
            self.application.add_handler(CommandHandler(command, handler))
            await logger.debug(f"Успешно: {desc} (/{command})")
        except Exception as e:
            await logger.error(f"Ошибка регистрации /{command}: {e}")
            raise


def main() -> None:
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print("\nБот остановлен")
    except Exception as e:
        print(f"Фатальная ошибка: {e}")

if __name__ == '__main__':
    main()