import telebot
from dotenv import load_dotenv
import os
import pg8000
from pg8000.native import Connection, DatabaseError
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ForceReply

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

# Хранилище временных данных пользователей
user_data = {}

def get_db_connection():
    """Унифицированная функция подключения к БД"""
    try:
        return Connection(**DB_CONFIG)
    except DatabaseError as e:
        print(f"Ошибка подключения к БД: {e}")
        raise

def is_admin(username):
    """Проверка прав администратора"""
    conn = get_db_connection()
    try:
        result = conn.run(
            "SELECT id FROM admins WHERE username = :username", 
            username=username
        )
        return len(result) > 0
    finally:
        conn.close()

def get_calculation_params():
    """Получение текущих параметров расчета"""
    conn = get_db_connection()
    try:
        result = conn.run("""
            SELECT param_name, param_value, description 
            FROM calculation_params
            ORDER BY param_name
        """)
        return result
    finally:
        conn.close()

def update_param(param_name, new_value):
    """Обновление параметра расчета"""
    conn = get_db_connection()
    try:
        conn.run(
            """
            UPDATE calculation_params 
            SET param_value = :value, updated_at = NOW() 
            WHERE param_name = :name
            """,
            value=new_value, name=param_name
        )
    finally:
        conn.close()

def format_params(params):
    """Форматирование параметров для отображения"""
    return "\n".join([
        f"{row[0]}: {row[1]} ({row[2]})" 
        for row in params
    ])

@bot.message_handler(commands=['start'])
def handle_start(message):
    """Главное меню администратора"""
    # if not is_admin(message.from_user.username):
    #     bot.reply_to(message, "⛔ У вас нет прав доступа!")
    #     return

    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("Управление параметрами"))

    bot.send_message(
        message.chat.id,
        "🛡️ Добро пожаловать в панель администратора!",
        reply_markup=markup
    )

@bot.message_handler(func=lambda m: m.text == "Управление параметрами")
def handle_params_menu(message):
    """Меню управления параметрами"""
    # if not is_admin(message.from_user.username):
    #     return

    params = get_calculation_params()
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    
    # Добавляем кнопки для каждого параметра
    for param in params:
        markup.add(KeyboardButton(f"✏️ Изменить {param[0]}"))
    
    markup.add(KeyboardButton("🔙 Назад"))

    bot.send_message(
        message.chat.id,
        f"📋 Текущие параметры расчета:\n\n{format_params(params)}\n\n"
        "Выберите параметр для изменения:",
        reply_markup=markup
    )

@bot.message_handler(func=lambda m: m.text.startswith('✏️ Изменить '))
def select_param_to_edit(message):
    """Обработчик выбора параметра для редактирования"""
    # if not is_admin(message.from_user.username):
    #     return

    param_name = message.text.replace("✏️ Изменить ", "")
    user_data[message.chat.id] = {'editing_param': param_name}

    bot.send_message(
        message.chat.id,
        f"Введите новое значение для параметра '{param_name}':",
        reply_markup=ForceReply()
    )

@bot.message_handler(func=lambda m: user_data.get(m.chat.id, {}).get('editing_param'))
def process_param_update(message):
    """Обработка обновления параметра"""
    # if not is_admin(message.from_user.username):
    #     return

    param_name = user_data[message.chat.id]['editing_param']
    
    try:
        new_value = float(message.text)
        update_param(param_name, new_value)
        
        bot.send_message(
            message.chat.id,
            f"✅ Параметр '{param_name}' успешно обновлен на значение: {new_value}"
        )
        
        # Возвращаемся в меню параметров
        handle_params_menu(message)
        
    except ValueError:
        bot.send_message(
            message.chat.id,
            "❌ Ошибка: необходимо ввести числовое значение"
        )
    finally:
        if message.chat.id in user_data:
            del user_data[message.chat.id]['editing_param']

@bot.message_handler(func=lambda m: m.text == "🔙 Назад")
def handle_back(message):
    """Обработчик кнопки Назад"""
    handle_start(message)

if __name__ == '__main__':
    bot.polling(none_stop=True)