from telegram import Update
from telegram.ext import ContextTypes
import logging
from dotenv import load_dotenv
import os
import requests
import random
from datetime import datetime, timedelta
import re

load_dotenv()
logger = logging.getLogger(__name__)

class Handlers:
    def __init__(self, db=None):
        self.bot_names = ["бот", "лёва", "лимонадный", "дружище", "лева", "лев"]
        self.db = db
        self.command_patterns = {
            r'(^|\s)(шутк|анекдот|пошути|рассмеши)': self.joke,
            r'(^|\s)(расскажи|дай|хочу|го)\s*(шутку|анекдот)': self.joke,            
            r'(^|\s)(какая|узнать|скажи)\s*(погода|погоду)\s*(в|по)?\s*([а-яё]+)': self.weather,
            r'(^|\s)(погода|погоду)\s*(в|по)?\s*([а-яё]+)': self.weather,
            r'(^|\s)(команды|что умеешь|помощь|help)': self.info,
            r'(^|\s)(звания|розыгрыш|титулы)': self.assign_titles,
            r'(^|\s)(старт|начать|привет|hello)': self.start_handler,
            r'(^|\s)(цтт)': lambda u, c: self.handle_quote_command(u, c),
            r'(^|\s)(старт|начать|привет|hello)': lambda u, c: self.start_handler(u, c)
        }
        
    def is_message_for_bot(self, text: str) -> bool:
    
        if not text:
            return False
            
        first_word = text.split()[0].lower()
        if first_word in self.bot_names:
            return True
            
        return any(name in text.lower() for name in self.bot_names)

    async def process_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    
        if update.message.reply_to_message and update.message.text.lower().strip() == "цтт":
            await self._add_quote_from_reply(update, context)
            return
        
        user_text = update.message.text.lower() if update.message.text else ""
    
        if not self.is_message_for_bot(user_text):
            return

        cleaned_text = re.sub(r'^\s*(бот|лёва|лева|дружище)[,\.!]*\s*', '', user_text)
    
    
        for pattern, handler in self.command_patterns.items():
            if re.search(pattern, cleaned_text):
                await handler(update, context)  # Все обработчики теперь принимают только update и context
                return
            
        await self.handle_text(update, context)

    async def start_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        
        try:
            await update.message.reply_text(
                f"Привет! Я бот Лёва. Можешь попросить меня:\n"
                f"- Рассказать шутку\n"
                f"- Сообщить погоду\n"
                f"- Разыграть звания в чате\n"
                f"Просто напиши что-то вроде 'Лёва, расскажи шутку'"
            )
        except Exception as e:
            logger.error(f"Start error: {e}")
            await update.message.reply_text("Не смог обработать запрос")

    async def weather(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Обработчик запросов погоды"""
        try:
            # Ищем город в тексте
            match = re.search(r'погод[а-я]*\s*(?:в|по)?\s*([а-яё]+)', text)
            city = match.group(1) if match else None
            
            if not city:
                await update.message.reply_text("Напиши например: 'Лева, какая погода в Москве?' или 'Лева, погода в Питере'")
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
            logger.error(f"Ошибка в погоде: {e}")
            await update.message.reply_text("Произошла ошибка при запросе погоды. Попробуй позже.")

    async def joke(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Обработчик запросов шуток"""
        try:
            url = "http://rzhunemogu.ru/RandJSON.aspx?CType=1"  
            response = requests.get(url, timeout=5)
            
            if response.status_code != 200:
                await update.message.reply_text("Не удалось получить шутку. Попробуй позже.")
                return
        
            joke_text = response.text.replace('{"content":"', '').replace('"}', '')
            await update.message.reply_text(joke_text)

        except Exception as e:
            logger.error(f"Ошибка в шутке: {e}")
            await update.message.reply_text("Произошла ошибка при получении шутки. Попробуй позже.")

    async def info(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        
        try:
            commands = [
                "Как общаться со мной:",
                "- 'Лёва, расскажи шутку'",
                "- 'Лёва, какая погода в Москве'",
                "- 'Лёва, разыграй звания'",
                "- 'Лёва, что ты умеешь?'"
            ]
            await update.message.reply_text("\n".join(commands))
        except Exception as e:
            logger.error(f"Ошибка в info: {e}")
            await update.message.reply_text("Произошла ошибка. Попробуй позже.")
    
    async def assign_titles(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        
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
            
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE, cleaned_text: str):
        
        greetings = ["Привет-привет! 😃", "Здорово, что заглянул! 👍", "Йоу! Чё как? 😎"]
        farewells = ["Пока-пока! 🖐️", "Уже уходишь? Ну ладно... 😢", "До скорого! 🥺"]

        if any(word in cleaned_text for word in ["привет", "здравствуй", "хай"]):
            await update.message.reply_text(random.choice(greetings))
        elif any(word in cleaned_text for word in ["пока", "до свидания", "прощай"]):
            await update.message.reply_text(random.choice(farewells))
        elif "как тебя зовут" in cleaned_text:
            await update.message.reply_text("Меня зовут Лёва Лимонадов! 🎉")
        else:
            neutral_answers = [
                "Честно говоря, я не понял... 🤔",
                "Можешь перефразировать? 🧐",
                "Попробуй сказать 'Лёва, что ты умеешь?'"
            ]
            await update.message.reply_text(random.choice(neutral_answers))
            
            
            
    async def _add_quote_from_reply(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
  
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
            
            
            
    # Временный дебагхантер
    
    async def handle_quote_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    
        self.db.debug_quotes()  
    
        quote = self.db.get_random_quote()
        print(f"DEBUG: Полученная цитата: {quote}")  
    
        if quote:
            await update.message.reply_text(f"Цитата #{quote['id']}:\n{quote['text']}")
        else:
            await update.message.reply_text("Нет одобренных цитат")        