from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
import logging

logger = logging.getLogger(__name__)


class Feedback:
    def __init__(self, form_url: str, admin_chat_id: Optional[int] = None):
        self.form_url = form_url
        self.admin_chat_id = admin_chat_id

    async def handle_feedback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        try:
            await update.message.reply_text(
                "📝 Оставьте ваш отзыв:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Открыть форму", url=self.form_url)]
                ])
            )

            if self.admin_chat_id:
                await context.bot.send_message(
                    chat_id=self.admin_chat_id,
                    text=f"👤 Пользователь @{update.effective_user.username} запросил форму обратной связи"
                )

        except Exception as e:
            logger.error(f"Ошибка обработки обратной связи: {e}")
            await update.message.reply_text("⚠️ Не удалось открыть форму обратной связи")