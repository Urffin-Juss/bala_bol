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
from models import QuoteDB, Feedback
from typing import Optional, Dict, Any
import asyncio



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
            r'предлож[иь]|иде[яю]$': self._handle_feedback
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

        try:
            if not update.message or not update.message.text:
                return

            text = update.message.text.lower()

            is_direct_address = any(
                re.match(rf'^{re.escape(name)}[\s,!?.]+', text)  # только в начале сообщения
                for name in self.bot_names
            )


            if not is_direct_address:
                return


            cleaned_text = re.sub(
                rf'^({"|".join(map(re.escape, self.bot_names))})[\s,!?.]*\s*',
                    '',
                text
            )

            if re.match(r'^(?:какая\s+)?погод[а-я]*\b', cleaned_text):
                # передаём ОЧИЩЕННЫЙ текст
                await self.weather(update, context, cleaned_text=cleaned_text)
                return

            for pattern, handler in self.command_patterns.items():
                if re.fullmatch(pattern, cleaned_text.strip()):
                    logger.info(f"Обработка команды: {pattern}")
                    # Если это погода — пробросим очищенный текст
                    if handler is self.weather:
                        await handler(update, context, cleaned_text=cleaned_text)
                    else:
                        await handler(update, context)
                    return


            await update.message.reply_text("Не понимаю команду. Напиши 'помощь' для списка команд")

        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}", exc_info=True)
            await update.message.reply_text("⚠️ Произошла ошибка при обработке запроса")



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

    async def start_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        try:
            await update.message.reply_text(
                "Привет! Я бот Лёва. Вот что я умею:\n"
                "- Рассказывать шутки и анекдоты\n"
                "- Показывать погоду в любом городе\n"
                "- Разыгрывать звания в чате\n"
                "- Сохранять и показывать цитаты\n"
                "- Давать мудрые советы\n\n"
                "- Дать ссылочку на обратную связь\n\n"
                "Просто напиши что-то вроде 'Лёва, расскажи шутку'"
            )
        except Exception as e:
            logger.error(f"Ошибка в start_handler: {e}")
            await update.message.reply_text("Не смог обработать запрос")

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

    async def start_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        try:
            await update.message.reply_text(
                "Привет! Я бот Лёва. Вот что я умею:\n"
                "- Рассказывать шутки и анекдоты\n"
                "- Показывать погоду в любом городе\n"
                "- Разыгрывать звания в чате\n"
                "- Сохранять и показывать цитаты\n"
                "- Давать мудрые советы\n\n"
                "- Так же я могу дать ссылку на обратную связь\n\n"
                "Просто напиши что-то вроде 'Лёва, расскажи шутку'"
            )
        except Exception as e:
            logger.error(f"Ошибка в start_handler: {e}")
            await update.message.reply_text("Не смог обработать запрос")

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

    async def info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        try:
            commands = [
                "Как общаться со мной:",
                "- 'Лёва, расскажи шутку'",
                "- 'Лёва, какая погода в Москве'",
                "- 'Лёва, разыграй звания'",
                "- 'Лёва, что ты умеешь?'",
                "- 'Лёва, скажи мудрость'",
                "- 'Лева, вспомни цитату'"
                "- 'Лёва, что ты умеешь?'"
                "- 'Лёва, скажи мудрость'"
                "- 'Лева, вспомни цитату'"
            ]
            await update.message.reply_text("\n".join(commands))
        except Exception as e:
            logger.error(f"Ошибка в info: {e}")
            await update.message.reply_text("Произошла ошибка. Попробуй позже.")

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
        user = update.message.from_user

        if not original.text:
            await update.message.reply_text("⚠️ Можно сохранять только текстовые сообщения")
            return

        text = original.text.strip()

        if len(text) > 500:
            await update.message.reply_text("⚠️ Слишком длинная цитата (максимум 500 символов)")
            return

        if len(text) < 5:
            await update.message.reply_text("⚠️ Цитата слишком короткая")
            return

        try:
            if self.db.add_quote(user.id, user.full_name, text):
                username = f"@{user.username}" if user.username else user.full_name
                await update.message.reply_text("✅ Цитата успешно сохранена!")
                await original.reply_text(f"💾 Сохранено как цитата от {username}")
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
            if quote and 'text' in quote and 'user_name' in quote:
                response = f"📌 Цитата #{quote.get('id', '')}:\n\n{quote['text']}\n\n— {quote['user_name']}"
                await update.message.reply_text(response)
            else:
                await update.message.reply_text("📭 Пока нет сохранённых цитат")
        except Exception as e:
            logger.error(f"Ошибка при получении цитаты: {e}")
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

    # Временный дебагхантер

    async def handle_quote_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        self.db.debug_quotes()

        quote = self.db.get_random_quote()
        print(f"DEBUG: Полученная цитата: {quote}")

        if quote:
            await update.message.reply_text(f"Цитата #{quote['id']}:\n{quote['text']}")
        else:
            await update.message.reply_text("Нет одобренных цитат")        