from telegram.ext import Application, MessageHandler
from telegram import Update
import os
from handlers import Handlers


class Bot:
    def __init__(self, token):
        self.token = token
        self.application = Application.builder().token(self.token).build()
        self.handlers = Handlers()


    def setup_handlers(self):
        self.application.add_handlers (
            MessageHandler(filters.TEXT, self.handlers.handle.text)

        )