import logging
from typing import Dict, Any, Optional
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

class Feedback:
    def __init__(self, form_url: str, admin_chat_id: Optional[int] = None):
        """
        :param form_url: Ссылка на Google Forms
        :param admin_chat_id: ID чата админа для уведомлений
        """
        self.form_url = form_url
        self.admin_chat_id = admin_chat_id
        self.bot_names = ["лёва", "лева", "лимонадный", "бот", "дружище"]
        self.command_triggers = [
            "обратная связь", 
            "фидбек",
            "сообщить об ошибке",
            "багрепорт",
            "предложи идею"
        ]

    def register_handlers(self, handlers: 'Handlers'):
        """Регистрация обработчиков в основном классе Handlers"""
        for trigger in self.command_triggers:
            handlers.add_command_handler(trigger, self.handle_feedback)

    async def handle_feedback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик обратной связи"""
        try:
            user_data = {
                'id': update.effective_user.id,
                'username': update.effective_user.username or 'Нет username',
                'first_name': update.effective_user.first_name or 'Нет имени'
            }

            
            await update.message.reply_text(
                "📝 Помогите сделать меня лучше!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Открыть форму обратной связи", url=self.form_url)]
                ]),
                disable_web_page_preview=True
            )

            
            logger.info(f"Пользователь {user_data['id']} запросил форму обратной связи")

            
            if self.admin_chat_id:
                await context.bot.send_message(
                    chat_id=self.admin_chat_id,
                    text=f"📢 Пользователь @{user_data['username']} запросил форму обратной связи"
                )

        except Exception as e:
            logger.error(f"Ошибка в обработчике обратной связи: {e}")
            await update.message.reply_text("⚠️ Не удалось открыть форму. Попробуйте позже.")

    def get_usage_examples(self) -> list:
        """Возвращает примеры использования для команды info"""
        return [
            "- 'Лёва, обратная связь' - оставить отзыв",
            "- 'Лева, сообщить об ошибке' - сообщить о проблеме",
            "- 'бот, предложи идею' - предложить улучшение"
        ]

    def should_respond(self, text: str) -> bool:
        """Проверяет, относится ли сообщение к обратной связи"""
        text_lower = text.lower()
        return (
            any(trigger in text_lower for trigger in self.command_triggers) and
            any(name in text_lower for name in self.bot_names)
        ) or any(trigger in text_lower for trigger in self.command_triggers)