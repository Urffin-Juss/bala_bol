from telegram import Update
from telegram.ext import ContextTypes 
import logging
from dotenv import load_dotenv
import os
import requests
import random
from datetime import datetime, timedelta
from logger_service import logger


load_dotenv()


class Handlers:
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            context.user_data['name'] = update.message.from_user.first_name
            await update.message.reply_text(
                f"Привет, {context.user_data['name']}, я бот этого чата. "
                "Пока я не написан полностью, но тебе хорошего дня!"
            )
        except Exception as e:
            await logger.error(f"Ошибка в обработчике start: {e}")
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
                return

            url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=ru"
            response = requests.get(url)
            data = response.json()

            if data.get("cod") != 200:
                await update.message.reply_text(f"Не удалось получить погоду для города {city}. Проверьте название.")
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
                await logger.error(f"Ошибка при запросе к API: {e}")
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
 

            await logger.error(f"Ошибка в обработчике info: {e}")
 

            await update.message.reply_text("Произошла ошибка при получении списка команд. Попробуйте позже.")

    
    
    
    async def assing_titles(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            
            chat_id = update.message.chat.id
            last_called = context.chat_data.get('last_called')
            
            if last_called and datetime.now() - last_called < timedelta(hours=24) :
                await update.mesage.reply_text("Только один раз в сутки, котик")
            
            admins = await context.bot.get_chat_administrators(chat_id)
            
            human_members = [admin.user for admin in admins if not admin.user.is_bot]

            if len(human_members) < 2:
                await update.message.reply_text("В чате должно быть как минимум два участника!")
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
            await logger.error(f"Ошибка в обработчике assign_titles: {e}", exc_info=True)
            await update.message.reply_text("Произошла ошибка. Попробуйте позже.")        
            
 


