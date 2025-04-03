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

load_dotenv()
logger = logging.getLogger(__name__)

class Handlers:
    def __init__(self, db=None):
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")  
        self.deepseek_api_url = "https://api.deepseek.com/v1/chat/completions"      
        self.bot_names = ["бот", "лёва", "лимонадный", "дружище", "лева", "лев"]
        self.db = db
        self.wisdom_quotes = []
        
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
            
        self.command_patterns = {
            r'(^|\s)(шутк|анекдот|пошути|рассмеши)': lambda u, c: self.joke(u, c),
            r'(^|\s)(расскажи|дай|хочу|го)\s*(шутку|анекдот)': lambda u, c: self.joke(u, c),            
            r'(^|\s)(какая|узнать|скажи)\s*(погода|погоду)\s*(в|по)?\s*([а-яё]+)': lambda u, c: self.weather(u, c),
            r'(^|\s)(погода|погоду)\s*(в|по)?\s*([а-яё]+)': lambda u, c: self.weather(u, c),
            r'(^|\s)(команды|что умеешь|помощь|help)': lambda u, c: self.info(u, c),
            r'(^|\s)(звания|розыгрыш|титулы)': lambda u, c: self.assign_titles(u, c),
            r'(^|\s)(старт|начать|привет|hello)': lambda u, c: self.start_handler(u, c),
            r'(^|\s)(цтт)': lambda u, c: self.handle_quote_command(u, c),
            r'(?i)(^|\s)(мудрость|мудростью|скажи мудрость|дай мудрость)': lambda u, c: self.wisdom(u, c),
            r'(^|\s)(ответь|спроси|deepseek|ask)': lambda u, c: self.ask_deepseek(u, c)
        
            
        }

async def ask_deepseek(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    try:
       
        user_text = re.sub(
            r'(ответь|спроси|deepseek|ask)', 
            '', 
            update.message.text, 
            flags=re.IGNORECASE
        ).strip()
        
        if not user_text:
            await update.message.reply_text("Напишите вопрос после команды, например:\n'Лёва, ответь: как работает ИИ?'")
            return

        if not self.deepseek_api_key:
            await update.message.reply_text("API не настроен")
            logger.error("DeepSeek API key missing!")
            return

        headers = {
            "Authorization": f"Bearer {self.deepseek_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": user_text}],
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
       
        response = requests.post(
            self.deepseek_api_url,
            headers=headers,
            json=payload,
            timeout=15
        )
        
        
        if response.status_code != 200:
            error_msg = f"API error {response.status_code}: {response.text}"
            logger.error(error_msg)
            await update.message.reply_text("Ошибка при запросе к API")
            return
            
        answer = response.json()["choices"][0]["message"]["content"]
        
        
        clean_answer = answer.split("Ответ:")[-1].strip()
        clean_answer = clean_answer[:2000]  
        
        await update.message.reply_text(f"🤖 DeepSeek отвечает:\n\n{clean_answer}")
        
    except Exception as e:
        logger.error(f"DeepSeek error: {str(e)}")
        await update.message.reply_text("⚠️ Ошибка при обработке запроса")
    
    
    
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
                await handler(update, context)  
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

    async def weather(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        
        try:
            user_text = update.message.text.lower()
            match = re.search(r'погод[а-я]*\s*(?:в|по)?\s*([а-яё]+)', user_text)
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
                "- 'Лёва, что ты умеешь?'"
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
            
            
            
            
            
    # Временный дебагхантер
    
    async def handle_quote_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    
        self.db.debug_quotes()  
    
        quote = self.db.get_random_quote()
        print(f"DEBUG: Полученная цитата: {quote}")  
    
        if quote:
            await update.message.reply_text(f"Цитата #{quote['id']}:\n{quote['text']}")
        else:
            await update.message.reply_text("Нет одобренных цитат")        