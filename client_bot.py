import telebot
from dotenv import load_dotenv
import os
import pg8000
from pg8000.native import Connection, DatabaseError
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

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

# Хранилище временных данных пользователей
user_data = {}

def get_db_connection():
    """Создает подключение к базе данных"""
    try:
        return Connection(**DB_CONFIG)
    except DatabaseError as e:
        print(f"Ошибка подключения к БД: {e}")
        raise

def get_user_id(username):
    """Возвращает ID пользователя из БД по username"""
    conn = get_db_connection()
    try:
        result = conn.run(
            "SELECT id FROM users WHERE username = :username",
            username=username
        )
        return result[0][0] if result else None
    finally:
        conn.close()

def create_user(user_data):
    """Создает нового пользователя и возвращает его ID"""
    conn = get_db_connection()
    try:
        result = conn.run(
            """
            INSERT INTO users 
            (username, first_name, last_name, created_at, updated_at)
            VALUES (:username, :first_name, :last_name, NOW(), NOW())
            RETURNING id
            """,
            username=user_data['username'],
            first_name=user_data['first_name'],
            last_name=user_data['last_name']
        )
        return result[0][0]
    finally:
        conn.close()

def save_calculation(user_id, data):
    """Сохраняет расчет в БД"""
    conn = get_db_connection()
    try:
        conn.run(
            """
            INSERT INTO calculations 
            (user_id, cost, age, engine, volume, purpose, result_cost)
            VALUES (:user_id, :cost, :age, :engine, :volume, :purpose, :result_cost)
            """,
            user_id=user_id,
            cost=data['cost'],
            age=data['age'],
            engine=data['engine'],
            volume=data['volume'],
            purpose=data['purpose'],
            result_cost=data['result_cost']
        )
    finally:
        conn.close()

def calculate_price(data):
    """Функция расчета стоимости (заглушка)"""
    # TODO: Реализовать реальный расчет
    cost_jpy = data['cost']
    age = data['age']
    engine_type = data['engine']
    volume = data['volume']
    purpose = data['purpose']
    
    # Пример простого расчета (замените на реальную логику)
    result_cost = cost_jpy * 0.008  # Примерный курс JPY to USD
    
    return {
        **data,
        'result_cost': int(result_cost)
    }

@bot.message_handler(commands=['start'])
def handle_start(message):
    user = message.from_user
    user_info = {
        'username': user.username,
        'first_name': user.first_name or '',
        'last_name': user.last_name or ''
    }

    # Получаем или создаем пользователя
    user_id = get_user_id(user.username)
    if not user_id:
        user_id = create_user(user_info)

    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("Рассчитать стоимость автомобиля"))

    bot.send_message(message.chat.id, "Привет! Я бот для расчета стоимости авто из Японии")

    bot.send_message(
        message.chat.id,
        "Нажмите кнопку для расчета таможенной стоимости:",
        reply_markup=markup
    )

@bot.message_handler(func=lambda m: m.text == "Рассчитать стоимость автомобиля")
def start_calculation(message):
    user_data[message.chat.id] = {
        'step': 'cost',
        'username': message.from_user.username  # Сохраняем username для получения user_id позже
    }
    bot.send_message(message.chat.id, "Введите цену автомобиля в Японии в Йенах:")

@bot.message_handler(func=lambda m: user_data.get(m.chat.id, {}).get('step') == 'cost')
def get_cost(message):
    try:
        cost = int(message.text)
        if cost <= 0:
            raise ValueError
        user_data[message.chat.id]['cost'] = cost
        user_data[message.chat.id]['step'] = 'age'
        
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(KeyboardButton("Младше 3 лет"))
        markup.add(KeyboardButton("От 3 до 5 лет"))
        markup.add(KeyboardButton("Старше 5 лет"))
        
        bot.send_message(
            message.chat.id,
            "Выберите возраст автомобиля:",
            reply_markup=markup
        )
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректную сумму в Йенах (целое число больше 0)")

@bot.message_handler(func=lambda m: user_data.get(m.chat.id, {}).get('step') == 'age')
def get_age(message):
    age_mapping = {
        "Младше 3 лет": 1,
        "От 3 до 5 лет": 2,
        "Старше 5 лет": 3
    }
    
    if message.text not in age_mapping:
        bot.send_message(message.chat.id, "Пожалуйста, выберите вариант из предложенных")
        return
    
    user_data[message.chat.id]['age'] = age_mapping[message.text]
    user_data[message.chat.id]['step'] = 'engine'
    
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("Бензин или дизель"))
    markup.add(KeyboardButton("Электро"))
    
    bot.send_message(
        message.chat.id,
        "Выберите тип двигателя:",
        reply_markup=markup
    )

@bot.message_handler(func=lambda m: user_data.get(m.chat.id, {}).get('step') == 'engine')
def get_engine(message):
    engine_mapping = {
        "Бензин или дизель": 1,
        "Электро": 2
    }
    
    if message.text not in engine_mapping:
        bot.send_message(message.chat.id, "Пожалуйста, выберите вариант из предложенных")
        return
    
    user_data[message.chat.id]['engine'] = engine_mapping[message.text]
    user_data[message.chat.id]['step'] = 'volume'
    
    bot.send_message(
        message.chat.id,
        "Введите объем двигателя в см³ (целое число):",
        reply_markup=telebot.types.ReplyKeyboardRemove()
    )

@bot.message_handler(func=lambda m: user_data.get(m.chat.id, {}).get('step') == 'volume')
def get_volume(message):
    try:
        volume = int(message.text)
        if volume <= 0:
            raise ValueError
        user_data[message.chat.id]['volume'] = volume
        user_data[message.chat.id]['step'] = 'purpose'
        
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(KeyboardButton("Да, для личного пользования"))
        markup.add(KeyboardButton("Нет, для коммерческого использования"))
        
        bot.send_message(
            message.chat.id,
            "Автомобиль для личного пользования?",
            reply_markup=markup
        )
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректный объем двигателя (целое число больше 0)")

@bot.message_handler(func=lambda m: user_data.get(m.chat.id, {}).get('step') == 'purpose')
def get_purpose(message):
    if message.text not in ["Да, для личного пользования", "Нет, для коммерческого использования"]:
        bot.send_message(message.chat.id, "Пожалуйста, выберите вариант из предложенных")
        return
    
    purpose = message.text == "Да, для личного пользования"
    user_data[message.chat.id]['purpose'] = purpose
    
    # Получаем user_id из БД
    username = user_data[message.chat.id]['username']
    user_id = get_user_id(username)
    
    if not user_id:
        bot.send_message(message.chat.id, "Ошибка: пользователь не найден")
        return
    
    # Расчет стоимости
    calculation_data = calculate_price(user_data[message.chat.id])
    
    # Сохранение в БД
    save_calculation(user_id, calculation_data)
    
    # Отправка результата
    reply_markup = ReplyKeyboardMarkup(resize_keyboard=True)
    reply_markup.add(KeyboardButton("Рассчитать стоимость автомобиля"))

    inline_markup = telebot.types.InlineKeyboardMarkup()
    inline_markup.add(telebot.types.InlineKeyboardButton(
        "Оставить заявку", 
        url="https://t.me/miwka_84"
    ))

    bot.send_message(
        message.chat.id,
        f"Результат расчета:\n\n"
        f"Цена в Японии: {calculation_data['cost']} JPY\n"
        f"Возраст: {message.text}\n"
        f"Тип двигателя: {'Бензин/дизель' if calculation_data['engine'] == 1 else 'Электро'}\n"
        f"Объем: {calculation_data['volume']} см³\n"
        f"Назначение: {'Личное' if purpose else 'Коммерческое'}\n\n"
        f"Итоговая стоимость: {calculation_data['result_cost']} USD",
        reply_markup=inline_markup
    )

    # Затем отправляем сообщение с обычной клавиатурой
    bot.send_message(
        message.chat.id,
        "Выполнить новый расчет:",
        reply_markup=reply_markup
    )

    # Очищаем временные данные
    del user_data[message.chat.id]

if __name__ == '__main__':
    bot.polling(none_stop=True)