from telegram import Update
<<<<<<< HEAD
from telegram.ext import ContextTypes 
=======
from telegram.ext import ContextTypes
>>>>>>> global_update_april_2025
import logging
from dotenv import load_dotenv
import os
import requests
import random
from datetime import datetime, timedelta
<<<<<<< HEAD


load_dotenv()


logger = logging.getLogger(__name__)

class Handlers:
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            context.user_data['name'] = update.message.from_user.first_name
            await update.message.reply_text(
                f"Привет, {context.user_data['name']}, я бот этого чата. "
                "Пока я не написан полностью, но тебе хорошего дня!"
            )
        except Exception as e:
            logger.error(f"Ошибка в обработчике start: {e}")
            await update.message.reply_text("Произошла ошибка. Попробуйте позже.")

    async def weather(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            city = " ".join(context.args)
            if not city:
                await update.message.reply_text("Пожалуйста, укажите город. Например: /weather Москва")
                return

            api_key = os.getenv('OPENWEATHER_API_KEY')
            if not api_key:
                await update.message.reply_text("Ошибка: API-ключ для погоды не найден.")
=======
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
        self.bot_names = ["бот", "лёва", "лимонадный", "дружище", "лева", "лев"]
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
            r'какая погода(?: в| по)? [а-яё]{3,}$': self.weather,
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
                re.search(rf'(^|\s){re.escape(name)}[\s,!?.]', text)
                for name in self.bot_names
            )


            if not is_direct_address:
                return


            cleaned_text = re.sub(
                rf'^\s*({"|".join(map(re.escape, self.bot_names))})[\s,!?.]*\s*',
                '',
                text
            )


            for pattern, handler in self.command_patterns.items():
                if re.fullmatch(pattern, cleaned_text.strip()):
                    logger.info(f"Обработка команды: {pattern}")
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
                match = re.search(r'погод[а-я]*\s*(?:в|по)?\s*([а-яё]{3,})', user_text)
                city = match.group(1) if match else None

            if not city:
                await update.message.reply_text(
                    "Укажите город, например: 'Лева, какая погода в Москве?' или 'Лева, погода в Питере'")
                return


            api_key = os.getenv('OPENWEATHER_API_KEY')
            if not api_key:
                await update.message.reply_text("Ошибка: не могу получить данные о погоде.")
>>>>>>> global_update_april_2025
                return

            url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=ru"
            response = requests.get(url)
            data = response.json()

            if data.get("cod") != 200:
<<<<<<< HEAD
                await update.message.reply_text(f"Не удалось получить погоду для города {city}. Проверьте название.")
=======
                await update.message.reply_text(f"Не удалось получить погоду для города {city}. Проверь название.")
>>>>>>> global_update_april_2025
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
<<<<<<< HEAD
            logger.error(f"Ошибка в обработчике weather: {e}")
            await update.message.reply_text("Произошла ошибка при запросе погоды. Попробуйте позже.")

    async def joke(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            url = "http://rzhunemogu.ru/RandJSON.aspx?CType=1"  
            logger.info(f"Запрос к API: {url}")

            try:
                response = requests.get(url, timeout=5)  
                logger.info(f"Ответ API: {response.status_code}")
            except requests.exceptions.RequestException as e:
                logger.error(f"Ошибка при запросе к API: {e}")
                await update.message.reply_text("Не удалось подключиться к API. Попробуйте позже.")
                return

        
            if response.status_code != 200:
                logger.error(f"Ошибка API: {response.status_code} - {response.text}")
                await update.message.reply_text("Не удалось получить шутку. Попробуйте позже.")
                return

        
            try:
        
                joke_text = response.text.replace('{"content":"', '').replace('"}', '')
                logger.info(f"Данные API: {joke_text}")
            except Exception as e:
                logger.error(f"Ошибка при обработке ответа API: {e}")
                await update.message.reply_text("Не удалось обработать шутку. Попробуйте позже.")
                return

    
            await update.message.reply_text(joke_text)

        except Exception as e:
        
        
            logger.error(f"Ошибка в обработчике joke: {e}", exc_info=True)
            await update.message.reply_text("Произошла ошибка при получении шутки. Попробуйте позже.")


    async def info(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

 

        try:
 

        
 

            commands = [
 

                "/start - Начать работу с ботом",
 

                "/weather <город> - Узнать погоду в указанном городе",
 

                "/joke - Получить случайную шутку",
 

                "/info - Показать список доступных команд",

                "/titles - розыгрыш званий"
 

            ]
 


 


 

            await update.message.reply_text("Доступные команды:\n" + "\n".join(commands))
 

        except Exception as e:
 

            logger.error(f"Ошибка в обработчике info: {e}")
 

            await update.message.reply_text("Произошла ошибка при получении списка команд. Попробуйте позже.")

    
    
    
    async def assing_titles(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            
            chat_id = update.message.chat.id
            last_called = context.chat_data.get('last_called')
            
            if last_called and datetime.now() - last_called < timedelta(hours=24) :
                await update.message.reply_text("Только один раз в сутки, котик")
                return
            
            admins = await context.bot.get_chat_administrators(chat_id)
            
            human_members = [admin.user for admin in admins if not admin.user.is_bot]

            if len(human_members) < 2:
                await update.message.reply_text("В чате должно быть как минимум два участника!")
                return
            
            
            
            chosen_members = random.sample(human_members, 2)
            title_x = chosen_members[0]
            title_y = chosen_members[1]
            
            
            result_message = (
                
=======
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

    async def weather(self, update: Update, context: ContextTypes.DEFAULT_TYPE, city: Optional[str] = None):

        try:
            if not city:
                user_text = update.message.text.lower()
                match = re.search(r'погод[а-я]*\s*(?:в|по)?\s*([а-яё]+)', user_text)
                city = match.group(1) if match else None

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
>>>>>>> global_update_april_2025
                f"🎉 Сегодняшние звания:\n"
                f"🏆 Кисо чата: {title_x.mention_html()}\n"
                f"🥇 ХУЙ чата: {title_y.mention_html()}"
            )

<<<<<<< HEAD

            sent_message = await update.message.reply_text(result_message, parse_mode="HTML")

            await context.bot.pin_chat_message(chat_id, sent_message.message_id)

            context.chat_data["last_called"] = datetime.now()

        except Exception as e:
            logger.error(f"Ошибка в обработчике assign_titles: {e}", exc_info=True)
            await update.message.reply_text("Произошла ошибка. Попробуйте позже.")
            
 


=======
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
            
            
            
            
            


    # Временный дебагхантер

    async def handle_quote_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        self.db.debug_quotes()

        quote = self.db.get_random_quote()
        print(f"DEBUG: Полученная цитата: {quote}")

        if quote:
            await update.message.reply_text(f"Цитата #{quote['id']}:\n{quote['text']}")
        else:
            await update.message.reply_text("Нет одобренных цитат")        
>>>>>>> global_update_april_2025
