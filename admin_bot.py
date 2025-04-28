import telebot
from dotenv import load_dotenv
import os
import pg8000
from pg8000.native import Connection, DatabaseError

load_dotenv()

DB_CONFIG = {
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': int(os.getenv('DB_PORT'))
}

API_TOKEN = os.getenv('ADMIN_BOT')

bot = telebot.TeleBot(API_TOKEN)

def get_db_connection():
    try:
        return Connection(**DB_CONFIG)
    except DatabaseError as e:
        print(f"Admin bot DB error: {e}")
        raise

def is_admin(username):
    conn = get_db_connection()
    try:
        result = conn.run(
            "SELECT id FROM admins WHERE username = :username", 
            username=username
        )
        return len(result) > 0
    finally:
        conn.close()

@bot.message_handler(commands=['start'])
def handle_start(message):
    # user = message.from_user
    # if is_admin(user.username):
    #     bot.reply_to(message, "🛡️ Добро пожаловать, администратор!")
    # else:
    #     bot.reply_to(message, "⛔ У вас нет прав доступа!")
    bot.reply_to(message, "🛡️ Добро пожаловать, администратор!")

if __name__ == '__main__':
    bot.polling(none_stop=True)