import random
from telegram import Update
from telegram.ext import ContextTypes

class Handlers:
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_text = update.message.text
        response = self.generate_response(user_text)

        if response is not None:
            await update.message.reply_text(response) 

    def generate_response(self, text):
        text = text.lower()
        bot_names = ["бот", "лёва", "лимонадный", "дружище"]

        name_mentioned = any(name in text for name in bot_names)
        if not name_mentioned:
            return None

        cleaned_text = text
        for name in bot_names:
            cleaned_text = cleaned_text.replace(name, "").strip()

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
            return random.choice(greetings)

        elif any(word in cleaned_text for word in ["пока", "до свидания", "прощай"]):
            return random.choice(farewells)

        elif "как тебя зовут" in cleaned_text:
            return "Меня зовут Весёлый Бот! 🎉"

        elif "шутка" in cleaned_text:
            return "Что программист сказал перед смертью? ...01010100 01101000 01110010 01100101 01110011 01101000 01101111 01101100 01100100 😆"

        else:
            neutral_answers = [
                "Честно говоря, я не понял... 🤔",
                "Можешь перефразировать? 🧐",
                "Я пока только учусь. Спроси что-нибудь попроще! 😅"
            ]
            return random.choice(neutral_answers)