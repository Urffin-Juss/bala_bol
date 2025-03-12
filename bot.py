from telegram.ext import Application, CommandHandler
from telegram   import Update
import os
from handlers import Handlers


class Bot ():
    def __init__(self, token):
        self.token = token
        self.application = Application.builder().token(self.token).build()    
        self.handlers = Handlers()

    def setup_handlers(self):
        self.application.add_handler(CommandHandler("start", self.handlers.start))   
        self.application.add_handler(CommandHandler("weather", self.handlers.weather)) 
        self.application.add_handler(CommandHandler("joke", self.handlers.joke))
        self.application.add_handler(CommandHandler("info", self.handlers.info))
        self.application.add_handler(CommandHandler("penis", self.handlers.penis))
        self.application.add_handler(CommandHandler("random", self.handlers.random))

    def run(self):
        self.setup_handlers()
        self.application.run_polling()      