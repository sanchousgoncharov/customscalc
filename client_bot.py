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

API_TOKEN = os.getenv('CLIENT_BOT')

bot = telebot.TeleBot(API_TOKEN)

def get_db_connection():
    """Создает подключение к базе данных"""
    try:
        return Connection(**DB_CONFIG)
    except DatabaseError as e:
        print(f"Ошибка подключения к БД: {e}")
        raise

def user_exists(username):
    """Проверяет существование пользователя"""
    conn = get_db_connection()
    try:
        result = conn.run(
            "SELECT id FROM users WHERE username = :username",
            username=username
        )
        return len(result) > 0
    finally:
        conn.close()

def add_user(user_data):
    """Добавляет нового пользователя"""
    conn = get_db_connection()
    try:
        conn.run(
            """
            INSERT INTO users 
            (username, first_name, last_name, created_at, updated_at)
            VALUES (:username, :first_name, :last_name, NOW(), NOW())
            """,
            username=user_data['username'],
            first_name=user_data['first_name'],
            last_name=user_data['last_name']
        )
    finally:
        conn.close()

@bot.message_handler(commands=['start'])
def handle_start(message):
    user = message.from_user
    user_data = {
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name or ''  # last_name может быть None
    }
    
    if not user_exists(user.username):
        add_user(user_data)
        bot.reply_to(message, "Привет! Я чат-бот для расчета стоимости авто из Японии")
    else:
        bot.reply_to(message, "👋 С возвращением!")

if __name__ == '__main__':
    bot.polling(none_stop=True)