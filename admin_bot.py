import telebot
from dotenv import load_dotenv
import os

load_dotenv()

API_TOKEN = os.getenv('ADMIN_BOT')

bot = telebot.TeleBot(API_TOKEN)