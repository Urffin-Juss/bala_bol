import logging
from typing import Optional, Dict, Any

class Feedback:
    def __init__(self, form_url: str, admin_chat_id: Optional[int] = None):
        self.form_url = form_url
        self.admin_chat_id = admin_chat_id
        self.logger = logging.getLogger(__name__)
        
    def process_feedback(self, user: Dict[str, Any], text: str) -> None:
        """Обработка и сохранение фидбека"""
        self.logger.info(f"Feedback from {user['id']}: {text}")
        
        # Здесь можно добавить сохранение в БД или отправку админу
        if self.admin_chat_id:
            self._notify_admin(user, text)
    
    def _notify_admin(self, user: Dict[str, Any], text: str) -> None:
        """Отправка уведомления админу (заглушка)"""
        self.logger.info(f"Notifying admin about feedback from @{user.get('username')}")

    def get_form_url(self) -> str:
        """Возвращает ссылку на форму"""
        return self.form_url