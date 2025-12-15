"""
Inline клавиатуры для бота
"""
from telebot import types


def get_main_keyboard():
    """
    Главная клавиатура с основными функциями
    
    Returns:
        types.ReplyKeyboardMarkup: Клавиатура
    """
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    btn_weather = types.KeyboardButton("🌤️ Погода")
    btn_crypto = types.KeyboardButton("💰 Криптовалюта")
    btn_currency = types.KeyboardButton("💵 Валюта")
    btn_search = types.KeyboardButton("🔍 Поиск")
    btn_qr = types.KeyboardButton("📱 QR-код")
    btn_help = types.KeyboardButton("❓ Помощь")
    btn_status = types.KeyboardButton("📊 Статус")
    
    keyboard.add(btn_weather, btn_crypto)
    keyboard.add(btn_currency, btn_search)
    keyboard.add(btn_qr, btn_help)
    keyboard.add(btn_status)
    
    return keyboard


def get_remove_keyboard():
    """
    Удаление клавиатуры
    
    Returns:
        types.ReplyKeyboardRemove: Удаление клавиатуры
    """
    return types.ReplyKeyboardRemove()

