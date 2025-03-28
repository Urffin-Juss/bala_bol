import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import asyncio
from typing import Optional, Coroutine, Any





class AsyncBotLogger:
    def __init__(self, name: str, log_file: str= 'bot.log'):
        self._log_queue = asyncio.Queue()
        self._logger = self._setup_logger(name, log_file)
        self._running = True
        asyncio.create_task(self._process_logs())


    def _setup_logger(self, name: str, log_file: str) -> logging.Logger:
        logs_dir = Path('logs')
        logs_dir.mkdir(exist_ok=True)

        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)

        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        file_handler = RotatingFileHandler(
            logs_dir / log_file,
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding='utf-8'
        )

        return logger

    async def _process_logs(self):

            while self._running or not self._log_queue.empty():
                try:
                    log_task = await asyncio.wait_for(self._log_queue.get(), timeout=1.0)
                    await log_task
                    self._log_queue.task_done()
                except asyncio.TimeoutError:
                    continue

    async def _log(self, level: str, message: str, exc_info: Optional[BaseException] = None):

            log_method = getattr(self._logger, level)
            log_method(message, exc_info=exc_info)

    async def info(self, message: str):

            await self._log_queue.put(self._log('info', message))

    async def error(self, message: str, exc: Optional[BaseException] = None):

            await self._log_queue.put(self._log('error', message, exc))

    async def debug(self, message: str):

            await self._log_queue.put(self._log('debug', message))

    async def warning(self, message: str):

            await self._log_queue.put(self._log('warning', message))

    async def stop(self):

            self._running = False
            await self._log_queue.join()


    logger = AsyncBotLogger('bot')


    async def main():
        await logger.info("Бот запускается...")
        try:
            # Ваш код бота
            await logger.debug("Отладочная информация")
        except Exception as e:
            await logger.error("Критическая ошибка", exc_info=e)
        finally:
            await logger.stop()


