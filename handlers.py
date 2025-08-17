from telegram import Update
from telegram.ext import ContextTypes
import logging
from dotenv import load_dotenv
import os
import requests
import random
from datetime import datetime, timedelta
import re
from pathlib import Path
from models import QuoteDB, Feedback, GossipDB
from typing import Optional, Dict, Any
import asyncio
from html import escape




load_dotenv()
logger = logging.getLogger(__name__)


class Handlers:
    def __init__(self, db: QuoteDB, feedback: Feedback):

        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        self.deepseek_api_url = "https://api.deepseek.com/v1/chat/completions"
        self.bot_names = ["бот", "лев"]
        self.db = db
        self.feedback = feedback
        self.wisdom_quotes = []
        self.gossip_db = GossipDB()  # 👈 новое
        self.gossip_window_hours = int(os.getenv("GOSSIP_WINDOW_HOURS", "12"))
        self.gossip_limit = int(os.getenv("GOSSIP_LIMIT", "250"))
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        self.deepseek_api_url = os.getenv(
            "DEEPSEEK_API_URL",
            "https://api.deepseek.com/v1/chat/completions"
        ).strip()
        # === DeepSeek диалог ===
        self.dialog_on: dict[int, bool] = {}  # chat_id -> включён ли режим
        self.dialog_history: dict[int, list] = {}  # chat_id -> список сообщений
        self.DIALOG_MAX_TURNS = int(os.getenv("DIALOG_MAX_TURNS", "12"))  # сколько последних реплик держать
        self.DIALOG_MAX_CHARS = int(os.getenv("DIALOG_MAX_CHARS", "1500"))  # защита от “портянок”
        # системный промпт можно править в .env, иначе дефолт:
        self.dialog_system = os.getenv("DIALOG_SYSTEM",
                                       "Ты дружелюбный помощник по имени Лев. Отвечай кратко, по делу, на русском. "
                                       "Сохраняй контекст беседы. Если просят код — давай рабочие примеры. "
                                       "Если не уверен — уточняй.")

        # Загрузка цитат мудрости
        self._load_wisdom_quotes()

        # Паттерны команд
        self.command_patterns = {
            # Шутки (теперь требуют точного соответствия)
            r'шутк[ауи]|анекдот|пошути|рассмеши|прикол$': self.joke,
            r'расскажи шутку|дай шутку|хочу шутку|го шутку$': self.joke,

            # Погода (точное соответствие)
            r'(?:какая\s+)?погод[а-я]*.*$': self.weather,
            r'погода(?: в| по)? [а-яё]{3,}$': self.weather,

            # Информация
            r'команды|что умеешь|помощь|help|справка$': self.info,

            # Звания/титулы
            r'звания|розыгрыш|титулы|ранги$': self.assign_titles,

            # Приветствие (точное соответствие)
            r'старт$|начать$|привет$|hello$|hi$|здравствуй$': self.start_handler,

            # Цитаты
            r'цтт$|цитат[ауы]$|запомни$': self.handle_quote_command,

            # Мудрость
            r'мудрост[ьи]$|скажи мудрость$|дай мудрость$|совет$': self.wisdom,

            # DeepSeek
            r'ответь на вопрос (.+)$': self.ask_deepseek,
            r'(?:ответь|объясни|скажи|что думаешь) (.+)$': self.ask_deepseek,

            # Обратная связь
            r'обратн[аую]|фидбек|отзыв|сообщи об ошибке|багрепорт$': self._handle_feedback,
            r'предлож[иь]|иде[яю]$': self._handle_feedback,

            # Сплетни
            r'сплетн[иья]$|дай сплетни$|что новенького$': self.gossip,

            # Диалог
            r'диалог (?:включи|on|старт)$': self.dialog_enable,
            r'диалог (?:выключи|off|стоп)$': self.dialog_disable,
            r'диалог (?:сброс|забудь)$': self.dialog_reset_cmd,
            r'диалог статус$': self.dialog_status,






        }

    def _load_wisdom_quotes(self):

        try:
            current_dir = Path(__file__).parent
            quotes_file = current_dir / "data" / "wisdom_quotes.txt"
            with open(quotes_file, "r", encoding="utf-8") as f:
                for line in f:
                    if "|" in line:
                        text, author = line.strip().split("|", 1)
                        self.wisdom_quotes.append({
                            "text": text,
                            "author": author
                        })
            logger.info(f"Загружено {len(self.wisdom_quotes)} цитат мудрости")
        except Exception as e:
            logger.error(f"Ошибка загрузки цитат: {e}")
            self.wisdom_quotes = []

    async def _handle_feedback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        await self.feedback.handle_feedback(update, context)

    def is_message_for_bot(self, text: str) -> bool:

        text_lower = text.lower()
        return any(name in text_lower for name in self.bot_names)

    async def process_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Общая обработка входящих сообщений:
        - Логируем короткие тексты для "сплетен"
        - Реагируем только если обращение начинается с 'лев' / 'лёва'
        - Чистим обращение и маршрутизируем команду
        - Быстрый путь для погоды
        """
        try:
            # 0) Базовые проверки
            if not update.message or not update.message.text:
                return

            # 1) Логируем сообщение для "сплетен" (если включено и текст разумной длины)
            try:
                txt = update.message.text.strip()
                if getattr(self, "gossip_db", None) and 1 <= len(txt) <= 1000:
                    u = update.message.from_user
                    self.gossip_db.add_message(
                        chat_id=update.effective_chat.id,
                        user_id=(u.id if u else None),
                        user_name=(u.full_name if u else "Unknown"),
                        text=txt
                    )
            except Exception:
                # не мешаем основной логике, если логирование споткнулось
                pass

            # 2) Приводим к нижнему регистру
            text = update.message.text.lower()

            # 3) Реагируем только если имя бота стоит В НАЧАЛЕ
            is_direct_address = any(
                re.match(rf'^{re.escape(name)}[\s,!?.]+', text)
                for name in self.bot_names  # ожидается ["лёва", "лев"]
            )
            if not is_direct_address:
                return

            # 4) Убираем обращение ("лев", "лёва") и ведущие знаки/пробелы
            cleaned_text = re.sub(
                rf'^({"|".join(map(re.escape, self.bot_names))})[\s,!?.]*\s*',
                '',
                text
            ).strip()

            # 5) Быстрый путь для погоды (корректно парсим город дальше в self.weather)
            if re.match(r'^(?:какая\s+)?погод[а-я]*\b', cleaned_text):
                await self.weather(update, context, cleaned_text=cleaned_text)
                return

            # 6) Маршрутизация по известным паттернам
            for pattern, handler in self.command_patterns.items():
                if re.fullmatch(pattern, cleaned_text):
                    logger.info(f"Обработка команды по паттерну: {pattern}")
                    if handler is self.weather:
                        await handler(update, context, cleaned_text=cleaned_text)
                    else:
                        await handler(update, context)
                    return

            # 7) Если ничего не сматчилось
                if self._dialog_enabled(update.effective_chat.id):
                    # поддержим форму "диалог ..."
                    lt = cleaned_text.lower()
                    if lt.startswith("диалог "):
                        cleaned_text = cleaned_text[7:].strip()
                        if not cleaned_text:
                            await update.message.reply_text("Скажи что-нибудь для диалога 🙂")
                            return
                    await self.dialog_answer(update, context, cleaned_text)
                    return

            await update.message.reply_text("Не понимаю команду. Напиши 'помощь' для списка команд")

        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}", exc_info=True)
            await update.message.reply_text("⚠️ Произошла ошибка при обработке запроса")

    def _help_text(self) -> str:
        """Формирует текст справки с учётом включённых фич."""
        meteorf_on = getattr(self, "meteorf_enabled", False)
        gossip_on = getattr(self, "gossip_db", None) is not None
        deepseek_on = bool(getattr(self, "deepseek_api_key", None))

        lines = []
        lines.append("👋 <b>Привет!</b> Я Лев. Пиши моё имя в начале сообщения.\n")
        lines.append("📚 <b>Что я умею</b>:")

        # Погода (OpenWeather)
        lines.append("• 🌦 <b>Погода сейчас</b>:")
        lines.append("  <code>Лев погода Москва</code>")
        lines.append("  <code>Лев какая погода в Нью-Йорке</code>")

        # Прогноз MeteoRF — показываем только если включено
        if meteorf_on:
            lines.append("• 🗓 <b>Прогноз Гидрометцентра</b>:")
            lines.append("  <code>Лев прогноз Москва</code>")
            lines.append("  <code>Лев прогноз на неделю Казань</code>")

        # Цитаты
        lines.append("• 📝 <b>Цитаты из чата</b>:")
        lines.append("  — Сохранить (ответом на сообщение): <code>цтт</code>")
        lines.append("  — Случайная: <code>Лев цитата</code>  (покажу текст и автора)")

        # Шутки / мудрость
        lines.append("• 😂 <b>Шутки</b>: <code>Лев шутку</code>  |  🧠 <b>Мудрость</b>: <code>Лев мудрость</code>")

        # Сплетни
        if gossip_on:
            lines.append("• 🫖 <b>Сплетни</b> (дайджест чата): <code>Лев сплетни</code>")

        # DeepSeek QA
        if deepseek_on:
            lines.append("• 🤖 <b>Вопросы к ИИ</b>:")
            lines.append("  <code>Лев ответь на вопрос почему не работает VPN</code>")
            lines.append("  <code>Лев объясни как подключить вебхук</code>")

        # Звания
        lines.append("• 🏅 <b>Звания/розыгрыш</b>: <code>Лев звания</code>")

        # Обратная связь
        lines.append("• 📨 <b>Обратная связь</b>: <code>Лев фидбек</code> или <code>Лев предложение</code>")

        # Справка
        lines.append("\nℹ️ <b>Справка</b>: <code>Лев помощь</code> или <code>Лев команды</code>")
        lines.append("⚙️ Триггер: сообщение должно <u>начинаться</u> с «Лев» или «Лёва».")
        return "\n".join(lines)

        # Диалог
        lines.append("• 🗣 <b>Диалог с ИИ</b>:")
        lines.append("  <code>Лев диалог включи</code> / <code>Лев диалог выключи</code>")
        lines.append("  <code>Лев диалог сброс</code> / <code>Лев диалог статус</code>")

    async def start_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Приветствие + краткая инструкция."""
        try:
            user = update.effective_user.full_name if update.effective_user else "друг"
            text = f"Привет, {user}!\n\n" + self._help_text()
            await update.message.reply_text(text, parse_mode="HTML", disable_web_page_preview=True)
        except Exception as e:
            logger.error(f"start_handler error: {e}", exc_info=True)

    async def info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Полная справка по командам."""
        try:
            await update.message.reply_text(self._help_text(), parse_mode="HTML", disable_web_page_preview=True)
        except Exception as e:
            logger.error(f"info error: {e}", exc_info=True)

    async def weather(self, update: Update, context: ContextTypes.DEFAULT_TYPE, city: Optional[str] = None):

        try:

            if city is None:
                user_text = update.message.text.lower()
                match = re.search(r'погод[а-я]*\s*(?:в|по)?\s*([\w\- а-яё]{3,})$', user_text)
                city = match.group(1).strip() if match else None

            if not city:
                await update.message.reply_text(
                    "Укажите город, например: 'Лева, какая погода в Москве?' или 'Лева, погода в Питере'")
                return


            api_key = os.getenv('OPENWEATHER_API_KEY')
            if not api_key:
                await update.message.reply_text("Ошибка: не могу получить данные о погоде.")
                return

            url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=ru"
            response = requests.get(url)
            data = response.json()

            if data.get("cod") != 200:
                await update.message.reply_text(f"Не удалось получить погоду для города {city}. Проверь название.")
                return

            weather_description = data['weather'][0]['description']
            temperature = data['main']['temp']
            humidity = data['main']['humidity']
            wind_speed = data['wind']['speed']

            weather_message = (
                f"Погода в городе {city}:\n"
                f"Описание: {weather_description}\n"
                f"Температура: {temperature}°C\n"
                f"Влажность: {humidity}%\n"
                f"Скорость ветра: {wind_speed} м/с"
            )
            await update.message.reply_text(weather_message)

        except Exception as e:
            logger.error(f"Ошибка в weather: {e}")
            await update.message.reply_text("Произошла ошибка при запросе погоды. Попробуй позже.")

    async def wisdom(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        try:
            if not self.wisdom_quotes:
                await update.message.reply_text("База мудростей пока пуста 😢")
                return

            quote = random.choice(self.wisdom_quotes)
            response = f"«{quote['text']}»\n\n— {quote['author']}"
            await update.message.reply_text(response)

        except Exception as e:
            logger.error(f"Ошибка в wisdom: {e}")
            await update.message.reply_text("Произошла ошибка при поиске мудрости. Попробуй позже.")



    async def weather(
            self,
            update: Update,
            context: ContextTypes.DEFAULT_TYPE,
            city: Optional[str] = None,
            cleaned_text: Optional[str] = None
    ):
        try:
            # 1) город
            if not city:
                city = self._extract_city(cleaned_text or "")

            if not city:
                await update.message.reply_text(
                    "Укажи город, например: 'Лёва, какая погода в Казани?' или 'Лёва, погода в Нью-Йорке'"
                )
                return

            if not city:
                await update.message.reply_text(
                    "Укажите город, например: 'Лева, какая погода в Москве?' или 'Лева, погода в Питере'")
                return

            api_key = os.getenv('OPENWEATHER_API_KEY')
            if not api_key:
                await update.message.reply_text("Ошибка: не могу получить данные о погоде.")
                return

            url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=ru"
            response = requests.get(url)
            data = response.json()

            if data.get("cod") != 200:
                await update.message.reply_text(f"Не удалось получить погоду для города {city}. Проверь название.")
                return

            weather_description = data['weather'][0]['description']
            temperature = data['main']['temp']
            humidity = data['main']['humidity']
            wind_speed = data['wind']['speed']

            weather_message = (
                f"Погода в городе {city}:\n"
                f"Описание: {weather_description}\n"
                f"Температура: {temperature}°C\n"
                f"Влажность: {humidity}%\n"
                f"Скорость ветра: {wind_speed} м/с"
            )
            await update.message.reply_text(weather_message)


        except Exception as e:

            logger.error(f"Ошибка в weather: {e}", exc_info=True)

            await update.message.reply_text("Произошла ошибка при запросе погоды. Попробуй позже.")


    async def joke(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        try:
            url = "http://rzhunemogu.ru/RandJSON.aspx?CType=1"
            response = requests.get(url, timeout=5)

            if response.status_code != 200:
                await update.message.reply_text("Не удалось получить шутку. Попробуй позже.")
                return

            joke_text = response.text.replace('{"content":"', '').replace('"}', '')
            await update.message.reply_text(joke_text)
            pass
        except Exception as e:
            logger.error(f"Ошибка в шутке: {e}")
            await update.message.reply_text("Произошла ошибка при получении шутки. Попробуй позже.")



    async def assign_titles(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        try:
            chat_id = update.message.chat.id
            last_called = context.chat_data.get('last_called')

            if last_called and datetime.now() - last_called < timedelta(hours=24):
                await update.message.reply_text("Только один раз в сутки, котик")
                return

            admins = await context.bot.get_chat_administrators(chat_id)
            human_members = [admin.user for admin in admins if not admin.user.is_bot]

            if len(human_members) < 2:
                await update.message.reply_text("Нужно как минимум два участника!")
                return

            chosen_members = random.sample(human_members, 2)
            title_x = chosen_members[0]
            title_y = chosen_members[1]

            result_message = (
                f"🎉 Сегодняшние звания:\n"
                f"🏆 Кисо чата: {title_x.mention_html()}\n"
                f"🥇 ХУЙ чата: {title_y.mention_html()}"
            )

            sent_message = await update.message.reply_text(result_message, parse_mode="HTML")
            await context.bot.pin_chat_message(chat_id, sent_message.message_id)
            context.chat_data["last_called"] = datetime.now()

        except Exception as e:
            logger.error(f"Ошибка в assign_titles: {e}")
            await update.message.reply_text("Произошла ошибка. Попробуй позже.")

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        if not update.message or not update.message.text:
            return

        user_text = update.message.text.lower()
        greetings = ["Привет-привет! 😃", "Здорово, что заглянул! 👍", "Йоу! Чё как? 😎"]
        farewells = ["Пока-пока! 🖐️", "Уже уходишь? Ну ладно... 😢", "До скорого! 🥺"]

        if any(word in user_text for word in ["привет", "здравствуй", "хай"]):
            await update.message.reply_text(random.choice(greetings))
        elif any(word in user_text for word in ["пока", "до свидания", "прощай"]):
            await update.message.reply_text(random.choice(farewells))
        elif "как тебя зовут" in user_text:
            await update.message.reply_text("Меня зовут Лёва Лимонадов! 🎉")
        else:
            neutral_answers = [
                "Честно говоря, я не понял... 🤔",
                "Можешь перефразировать? 🧐",
                "Попробуй сказать 'Лёва, что ты умеешь?'"
            ]
            await update.message.reply_text(random.choice(neutral_answers))

    async def add_quote_from_reply(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.db:
            await update.message.reply_text("❌ Система цитат недоступна")
            return

        if not update.message.reply_to_message:
            await update.message.reply_text("⚠️ Это не ответ на сообщение")
            return

        original = update.message.reply_to_message

        # Текст только из текстовых сообщений (как и было)
        if not (original.text and original.text.strip()):
            await update.message.reply_text("⚠️ Можно сохранять только текстовые сообщения")
            return

        text = original.text.strip()
        if len(text) > 500:
            await update.message.reply_text("⚠️ Слишком длинная цитата (максимум 500 символов)")
            return
        if len(text) < 5:
            await update.message.reply_text("⚠️ Цитата слишком короткая")
            return

        # === ВАЖНО: определяем АВТОРА цитаты ===
        author_id = None
        author_name = "Неизвестный автор"

        if original.from_user:
            # Обычное сообщение в чате
            au = original.from_user
            author_id = au.id
            author_name = au.full_name
            author_display = f"@{au.username}" if au.username else au.full_name
        elif getattr(original, "forward_from", None):
            # Форвард с раскрытым автором
            au = original.forward_from
            author_id = au.id
            author_name = au.full_name
            author_display = f"@{au.username}" if au.username else au.full_name
        elif getattr(original, "forward_sender_name", None):
            # Форвард из канала/скрытого источника
            author_display = author_name = original.forward_sender_name
        else:
            # Фолбэк — на всякий случай
            author_display = author_name

        try:
            # Сохраняем автора исходного сообщения, а не сохраняющего пользователя
            if self.db.add_quote(author_id, author_name, text):
                await update.message.reply_text("✅ Цитата сохранена!")
                await original.reply_text(f"💾 Сохранено как цитата — {author_display}")
            else:
                await update.message.reply_text("❌ Не удалось сохранить цитату")
        except Exception as e:
            logger.error(f"Ошибка при сохранении цитаты: {e}", exc_info=True)
            await update.message.reply_text("⚠️ Произошла ошибка при сохранении")

    async def handle_quote_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.db:
            await update.message.reply_text("❌ Система цитат недоступна")
            return

        try:
            quote = self.db.get_random_quote()
            if not quote:
                await update.message.reply_text("📭 Пока нет сохранённых цитат")
                return

            # ожидаем, что в БД лежат хотя бы 'user_id' и 'user_name'
            author_id = quote.get('user_id') or quote.get('author_id') or 0
            author_name = quote.get('user_name') or quote.get('author_name') or "Неизвестный автор"

            author_fmt = await self._format_author(
                context=context,
                chat_id=update.effective_chat.id,
                author_id=author_id,
                author_name=author_name
            )

            response = (
                f"📌 Цитата #{quote.get('id', '')}:\n\n"
                f"{escape(quote['text'])}\n\n"
                f"— {author_fmt}"
            )
            await update.message.reply_text(response, parse_mode="HTML", disable_web_page_preview=True)

        except Exception as e:
            logger.error(f"Ошибка при получении цитаты: {e}", exc_info=True)
            await update.message.reply_text("⚠️ Ошибка при получении цитаты")

    async def ask_deepseek(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        MAX_TIMEOUT = 40
        MAX_RETRIES = 5

        try:
            if not self.is_message_for_bot(update.message.text):
                return

            if not self.deepseek_api_key:
                await update.message.reply_text("🔴 Сервис временно недоступен")
                return

            logger.debug(f"🔐 Ключ длиной: {len(self.deepseek_api_key)}")

            query = self._extract_query(update.message.text)
            if len(query) < 4:
                await update.message.reply_text("📝 Пожалуйста, задайте более конкретный вопрос (минимум 4 символа)")
                return

            headers = {
                "Authorization": f"Bearer {self.deepseek_api_key}",
                "Content-Type": "application/json",
                "Accept-Encoding": "gzip"
            }

            payload = {
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": query}],
                "temperature": 0.7,
                "max_tokens": 2000,
                "stream": False
            }

            for attempt in range(MAX_RETRIES):
                try:
                    response = requests.post(
                        self.deepseek_api_url,
                        headers=headers,
                        json=payload,
                        timeout=MAX_TIMEOUT  # Тайм-аут запроса
                    )

                    if response.status_code == 429:
                        retry_after = int(response.headers.get('Retry-After', 30))
                        await update.message.reply_text(
                            f"🔄 Слишком много запросов. Попробую через {retry_after} сек...")
                        await asyncio.sleep(retry_after)
                        continue

                    response.raise_for_status()
                    data = response.json()

                    if not data.get('choices'):
                        raise ValueError("Неверная структура ответа API")

                    answer = data['choices'][0].get('message', {}).get('content', '').strip()
                    if not answer:
                        raise ValueError("Пустой ответ от API")

                    await update.message.reply_text(answer[:4000], parse_mode="Markdown")
                    return

                except requests.exceptions.Timeout:
                    logger.warning(f"Таймаут запроса (попытка {attempt + 1}/{MAX_RETRIES})")
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(2 * (attempt + 1))  # Экспоненциальная задержка
                    continue

                except requests.exceptions.RequestException as e:
                    logger.error(f"Ошибка сети: {str(e)}")
                    break

                except ValueError as e:
                    logger.error(f"Ошибка данных: {str(e)}")
                    break

                except Exception as e:
                    logger.error(f"Неожиданная ошибка: {str(e)}")
                    break

            # Если все попытки исчерпаны
            error_message = "🔴 Не удалось получить ответ. Ошибка сети"
            logger.error(f"DeepSeek API failure: {error_message}")
            await update.message.reply_text(
                "😢 Не смог обработать запрос из-за технических проблем. "
                "Попробуйте задать вопрос позже или переформулируйте его."
            )

        except Exception as e:
            logger.error(f"Critical error in ask_deepseek: {str(e)}", exc_info=True)
            await update.message.reply_text("⚠️ Произошла критическая ошибка. Пожалуйста, попробуйте позже.")

    def _extract_query(self, text: str) -> str:


        for name in self.bot_names:
            text = re.sub(rf'^\s*{re.escape(name)}\s*[,!?.]*\s*', '', text, flags=re.IGNORECASE)
        return text.strip()

    def _extract_city(self, text: str) -> Optional[str]:
        """
        Извлекает город из текста вида:
        - 'погода волгоград'
        - 'погода в волгограде'
        - 'какая погода в нью-йорке'
        - 'погода по питеру'
        """
        text = text.strip().lower()

        # ищем слово 'погода' и всё, что после
        m = re.search(r'погода(?:\s+[впо])?\s+(.+)', text)
        if not m:
            return None

        city = m.group(1).strip()

        # уберём лишние знаки препинания
        city = re.sub(r'^[,.;:!?«»"\']+|[,.;:!?«»"\']+$', '', city)

        # нормализуем пробелы
        city = re.sub(r'\s{2,}', ' ', city)

        if len(city) < 3:
            return None
        return city

    from html import escape

    async def _format_author(self, context: ContextTypes.DEFAULT_TYPE, chat_id: int,
                             author_id: int | None, author_name: str | None) -> str:
        """
        Возвращает строку вида '@username (Имя Фамилия)' с кликабельным именем.
        Если username недоступен, вернёт просто кликабельное имя.
        Если user_id нет, вернёт обычный текст author_name.
        """
        name = author_name or "Неизвестный автор"

        if not author_id:
            # нет id — ссылку не сделаем
            return escape(name)

        username = None
        try:
            # Попробуем получить актуальный username из участников чата
            member = await context.bot.get_chat_member(chat_id, author_id)
            if member and member.user:
                username = member.user.username
                # обновим имя, если хранится пустое/устаревшее
                if member.user.full_name and member.user.full_name != name:
                    name = member.user.full_name
        except Exception:
            # юзер мог выйти из чата — это нормально
            pass

        link = f'<a href="tg://user?id={author_id}">{escape(name)}</a>'
        if username:
            return f"@{escape(username)} ({link})"
        return link

    async def gossip(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Пересказ последних событий чата за N часов."""
        try:
            chat_id = update.effective_chat.id
            msgs = self.gossip_db.get_recent(chat_id, hours=self.gossip_window_hours, limit=self.gossip_limit)

            if not msgs or len([m for m in msgs if m.get("text")]) < 5:
                await update.message.reply_text("Пока мало новостей. Пишите активнее — тогда будут сплетни 😉")
                return

            # соберём компактный контекст для LLM
            def fmt(m):
                name = m.get("user_name") or "Кто-то"
                txt = m.get("text", "").replace("\n", " ").strip()
                return f"{name}: {txt}"

            sample = "\n".join(fmt(m) for m in msgs[:180])  # ограничим контекст

            summary = None
            if self.deepseek_api_key:
                prompt = (
                    "Сделай краткий структурированный пересказ сообщений из группового чата за последние часы. "
                    "Выдели: 1) главные темы, 2) кто что предлагал/сделал, 3) договорённости и дедлайны, "
                    "4) забавные моменты (кратко). Пиши по-русски, списком, без лишней воды. "
                    "Если информация противоречива — отметь это. Вот лента сообщений (сверху новые):\n\n"
                    f"{sample}"
                )
                headers = {
                    "Authorization": f"Bearer {self.deepseek_api_key}",
                    "Content-Type": "application/json",
                    "Accept-Encoding": "gzip"
                }
                payload = {
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.4,
                    "max_tokens": 800,
                    "stream": False
                }
                try:
                    import requests
                    r = requests.post(self.deepseek_api_url, headers=headers, json=payload, timeout=35)
                    r.raise_for_status()
                    data = r.json()
                    summary = (data.get("choices", [{}])[0].get("message", {}) or {}).get("content")
                except Exception as e:
                    logger.warning(f"DeepSeek gossip summary failed: {e}")

            # Фолбэк без LLM
            if not summary:
                # Простая агрегирующая выжимка по повторяющимся словам/именам
                top_users = {}
                for m in msgs:
                    n = (m.get("user_name") or "Кто-то").split()[0]
                    top_users[n] = top_users.get(n, 0) + 1
                top = ", ".join([f"{k}×{v}" for k, v in sorted(top_users.items(), key=lambda x: -x[1])[:5]])
                summary = (
                    "Коротко по чату:\n"
                    f"• Сообщений: {len(msgs)} за {self.gossip_window_hours}ч\n"
                    f"• Самые активные: {top or '—'}\n"
                    "• Для детального пересказа подключите DeepSeek (DEEPSEEK_API_KEY).\n"
                )

            header = f"🫖 Сплетни за последние {self.gossip_window_hours}ч:"
            await update.message.reply_text(f"{header}\n\n{summary}".strip()[:4000])
        except Exception as e:
            logger.error(f"Ошибка в gossip: {e}", exc_info=True)
            await update.message.reply_text("Не вышло собрать сплетни. Попробуй позже.")
    """
    async def forecast(self, update, context, city: Optional[str] = None, cleaned_text: Optional[str] = None):
        try:
            # текст в двух видах: нижний для матчинга, исходный для извлечения города
            raw_full = update.message.text or ""
            # уберём обращение "Лев/Лёва" из оригинала, но БЕЗ .lower()
            orig_cleaned = re.sub(
                rf'^\s*({"|".join(map(re.escape, self.bot_names))})[\s,!?.]*\s*',
                '',
                raw_full,
                flags=re.IGNORECASE
            ).strip()

            lower_cleaned = (cleaned_text or orig_cleaned).lower()

            # weekly?
            is_weekly = bool(re.search(r'прогноз(?:\s+на)?\s+недел[юи]', lower_cleaned))

            # город вытаскиваем из ОРИГИНАЛА (orig_cleaned), чтобы сохранить регистр
            if not city:
                if is_weekly:
                    m = re.search(r'прогноз(?:\s+на)?\s+недел[юи](?:\s+(?:в|по))?\s+(.+)$', orig_cleaned,
                                  flags=re.IGNORECASE)
                else:
                    m = re.search(r'прогноз(?:\s+(?:в|по))?\s+(.+)$', orig_cleaned, flags=re.IGNORECASE)
                city = (m.group(1).strip() if m else None)

            if not city:
                await update.message.reply_text(
                    "Укажи город: 'Лев прогноз Москва' или 'Лев прогноз на неделю Москва'"
                )
                return


        except Exception as e:

            logger.error(f"Ошибка в forecast: {e}", exc_info=True)

            await update.message.reply_text("Не удалось получить прогноз. Попробуй позже.")

    async def station_search(self, update, context, cleaned_text: str = None, city: Optional[str] = None):
        try:
            raw_full = update.message.text or ""
            orig_cleaned = re.sub(
                rf'^\s*({"|".join(map(re.escape, self.bot_names))})[\s,!?.]*\s*',
                '',
                raw_full,
                flags=re.IGNORECASE
            ).strip()

            if not city:
                m = re.search(r'станц(?:ия|ии)?(?:\s+(?:в|по))?\s+(.+)$', orig_cleaned, flags=re.IGNORECASE)
                city = (m.group(1).strip() if m else None)

            if not city:
                await update.message.reply_text("Пример: 'Лев станции Москва'")
                return

            stations = self.meteorf.search_stations(city)
            if not stations:
                await update.message.reply_text(f"По '{city}' ничего не нашёл.")
                return

            lines = [f"Найдено станций для «{city}»: (до 10 шт.)"]
            for s in stations[:10]:
                nm = s.get("locale_name") or s.get("name") or "—"
                lines.append(f"• {nm} — код {s['code']}")
            lines.append("\nМожно запросить: 'Лев прогноз код <код>'")
            await update.message.reply_text("\n".join(lines))

        except Exception as e:
            logger.error(f"station_search error: {e}", exc_info=True)
            await update.message.reply_text("Ошибка при поиске станции.")

    async def forecast_by_code(self, update, context, cleaned_text: str = None):
        try:
            text = (cleaned_text or update.message.text or "").lower()
            m = re.search(r'прогноз код (\d{6,})$', text)
            if not m:
                await update.message.reply_text("Пример: 'Лев прогноз код 106747000'")
                return
            code = m.group(1)

            raw = self.meteorf.forecast_weekly(code) if "недел" in text else self.meteorf.forecast_daily(code)

            # универсальный разбор дней
            if isinstance(raw, list):
                days = raw
            elif isinstance(raw, dict):
                for key in ("days", "daily", "items", "list", "forecasts", "data"):
                    if isinstance(raw.get(key), list):
                        days = raw[key];
                        break
                else:
                    days = []
            else:
                days = []

            def pick(d, *keys, default=None):
                for k in keys:
                    if isinstance(d, dict) and d.get(k) is not None:
                        return d[k]
                return default

            def fnum(x):
                try:
                    return f"{float(x):.1f}"
                except:
                    return None

            lines = [f"🗓 Прогноз (код {code}):"]
            shown = 0
            for d in days:
                date = pick(d, "date", "day", "dt", default="")
                tmin = fnum(pick(d, "t_min", "tMinC", "temp_min", "tmin"))
                tmax = fnum(pick(d, "t_max", "tMaxC", "temp_max", "tmax"))
                descr = pick(d, "descr", "text", "condition", "weather", default="")
                parts = [str(date)]
                if tmin or tmax:
                    if tmin and tmax:
                        parts.append(f"{tmin}…{tmax}°C")
                    elif tmax:
                        parts.append(f"до {tmax}°C")
                    elif tmin:
                        parts.append(f"от {tmin}°C")
                if descr: parts.append(descr)
                line = " — ".join(p for p in parts if p)
                if line: lines.append(line); shown += 1
                if shown >= 7: break

            if shown == 0:
                lines.append("Не получилось распарсить ответ API. Попробуй другой код/город.")
            await update.message.reply_text("\n".join(lines))
        except Exception as e:
            logger.error(f"forecast_by_code error: {e}", exc_info=True)
            await update.message.reply_text("Ошибка при получении прогноза по коду.")
"""

    def _dialog_enabled(self, chat_id: int) -> bool:
        return bool(self.dialog_on.get(chat_id))

    def _dialog_reset(self, chat_id: int):
        self.dialog_history[chat_id] = []

    def _dialog_push(self, chat_id: int, role: str, content: str):
        if not content:
            return
        hist = self.dialog_history.setdefault(chat_id, [])
        # подрежем слишком длинные
        content = content.strip()
        if len(content) > self.DIALOG_MAX_CHARS:
            content = content[:self.DIALOG_MAX_CHARS] + " …"
        hist.append({"role": role, "content": content})
        # ограничим окно по последним репликам
        if len(hist) > self.DIALOG_MAX_TURNS * 2 + 2:
            self.dialog_history[chat_id] = hist[-(self.DIALOG_MAX_TURNS * 2 + 2):]

    def _dialog_build_messages(self, chat_id: int) -> list[dict]:
        msgs = [{"role": "system", "content": self.dialog_system}]
        msgs.extend(self.dialog_history.get(chat_id, []))
        return msgs

    async def dialog_enable(self, update, context):
        chat_id = update.effective_chat.id
        self.dialog_on[chat_id] = True
        # не сбрасываем историю, чтобы можно было “догнать” после включения; при желании — разкомментируй:
        # self._dialog_reset(chat_id)
        await update.message.reply_text("🟢 Диалог с контекстом включён. Пиши: «Лев …» и я буду помнить беседу.")

    async def dialog_disable(self, update, context):
        chat_id = update.effective_chat.id
        self.dialog_on[chat_id] = False
        await update.message.reply_text("⛔ Диалог выключен. Команды работают как обычно.")

    async def dialog_reset_cmd(self, update, context):
        chat_id = update.effective_chat.id
        self._dialog_reset(chat_id)
        await update.message.reply_text("♻️ История диалога очищена.")

    async def dialog_status(self, update, context):
        chat_id = update.effective_chat.id
        on = "включён" if self._dialog_enabled(chat_id) else "выключен"
        turns = len(self.dialog_history.get(chat_id, []))
        await update.message.reply_text(f"ℹ️ Диалог {on}. В истории {turns} реплик.")

    async def dialog_answer(self, update, context, cleaned_text: str):
        """Отвечает через DeepSeek с сохранением контекста истории."""
        chat_id = update.effective_chat.id
        user_text = cleaned_text.strip()

        # записываем юзера и спрашиваем модель
        self._dialog_push(chat_id, "user", user_text)
        msgs = self._dialog_build_messages(chat_id)
        reply = self._deepseek_chat(msgs)
        self._dialog_push(chat_id, "assistant", reply)

        # отправляем
        await update.message.reply_text(reply)

    def _deepseek_chat(self, messages: list[dict], temperature: float = 0.4, max_tokens: int = 800) -> str:
        """
        Универсальный вызов DeepSeek ChatCompletion.
        messages: [{"role":"system|user|assistant", "content":"..."}]
        """
        if not self.deepseek_api_key:
            return "DeepSeek недоступен: не задан ключ (DEEPSEEK_API_KEY)."

        headers = {
            "Authorization": f"Bearer {self.deepseek_api_key}",
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip",
        }
        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        try:
            import requests
            r = requests.post(self.deepseek_api_url, headers=headers, json=payload, timeout=35)
            r.raise_for_status()
            data = r.json()
            msg = (data.get("choices", [{}])[0].get("message", {}) or {}).get("content")
            return msg or "Пустой ответ от модели."
        except Exception as e:
            logger.error(f"DeepSeek chat error: {e}", exc_info=True)
            return "Не удалось получить ответ от DeepSeek."
