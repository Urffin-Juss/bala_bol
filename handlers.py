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
    def __init__(self):
        self.bot_names = ["бот", "лёва", "лимонадный", "дружище", "лева", "лев"]
        self.bot_mention_pattern = re.compile(
            r'\b(бот|лёва|лимонадный|дружище|лева|лев)[,\.!]*\b',
            re.IGNORECASE
        )
        # Изменяем структуру хранения команд
        self.command_keywords = {
            "погода": "weather",
            "шутка": "joke",
            "команды": "info",
            "звания": "assign_titles",
            "старт": "start"
        }

    def is_message_for_bot(self, text: str) -> bool:
        """Проверяет, обращается ли пользователь к боту"""
        if not text:
            return False
            
        if self.bot_mention_pattern.search(text):
            return True
            
        first_word = text.split()[0].lower()
        if first_word in self.bot_names:
            return True
            
        return False

    async def process_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_text = update.message.text
        
        if not self.is_message_for_bot(user_text):
            return
            
        cleaned_text = self.bot_mention_pattern.sub('', user_text).strip()
        cleaned_text = cleaned_text.lower()

        for keyword, method_name in self.command_keywords.items():
            if keyword in cleaned_text:
                method = getattr(self, method_name)
                await method(update, context)
                return
                
        await self.handle_text(update, context, cleaned_text)

    async def weather(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды погоды"""
        try:
            user_text = update.message.text.lower()
            city = None
            
            if "погода" in user_text:
                parts = user_text.split("погода")[1].strip().split()
                if parts:
                    city = parts[0]
            
            if not city:
                await update.message.reply_text("Напиши мне, например: 'Лёва, какая погода в Москве?'")
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

    async def joke(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды шутки"""
        try:
            url = "http://rzhunemogu.ru/RandJSON.aspx?CType=1"  
            response = requests.get(url, timeout=5)
            
            if response.status_code != 200:
                await update.message.reply_text("Не удалось получить шутку. Попробуй позже.")
                return
        
            joke_text = response.text.replace('{"content":"', '').replace('"}', '')
            await update.message.reply_text(joke_text)

        except Exception as e:
            logger.error(f"Ошибка в joke: {e}")
            await update.message.reply_text("Произошла ошибка при получении шутки. Попробуй позже.")

    async def info(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды информации"""
        try:
            commands = [
                "бот/лёва + [команда] - обращение к боту",
                "погода [город] - узнать погоду",
                "шутка - получить случайную шутку",
                "команды - показать это сообщение",
                "звания - розыгрыш званий (раз в сутки)"
            ]
            await update.message.reply_text("Как со мной общаться:\n" + "\n".join(commands))
        except Exception as e:
            logger.error(f"Ошибка в info: {e}")
            await update.message.reply_text("Произошла ошибка. Попробуй позже.")
    
    async def assign_titles(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды розыгрыша званий"""
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
        """Обработчик общего текста"""
        greetings = [
            "Привет-привет! 😃",
            "Здорово, что заглянул! 👍", 
            "Йоу! Чё как? 😎"
        ]

        farewells = [
            "Пока-пока! 🖐️",
            "Уже уходишь? Ну ладно... 😢",
            "До скорого! Мне будет скучно... 🥺"
        ]

        if any(word in cleaned_text for word in ["привет", "здравствуй", "хай"]):
            await update.message.reply_text(random.choice(greetings))
        elif any(word in cleaned_text for word in ["пока", "до свидания", "прощай"]):
            await update.message.reply_text(random.choice(farewells))
        elif "как тебя зовут" in cleaned_text:
            await update.message.reply_text("Меня зовут Лёва! 🎉")
        elif "шутка" in cleaned_text:
            await self.joke(update, context)
        elif "погода" in cleaned_text:
            await self.weather(update, context)
        elif any(word in cleaned_text for word in ["команды", "что умеешь"]):
            await self.info(update, context)
        elif "звания" in cleaned_text:
            await self.assign_titles(update, context)
        else:
            neutral_answers = [
                "Честно говоря, я не понял... 🤔",
                "Можешь перефразировать? 🧐",
                "Я пока только учусь. Спроси что-нибудь попроще! 😅",
                "Попробуй сказать 'Лёва, что ты умеешь?'"
            ]
            await update.message.reply_text(random.choice(neutral_answers))