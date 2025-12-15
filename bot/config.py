"""
Конфигурация бота
"""
import os
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# OpenAI API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Настройки AI-агента
AI_MODEL = os.getenv("AI_MODEL", "gpt-4")
AI_TEMPERATURE = float(os.getenv("AI_TEMPERATURE", "0.7"))

# Настройки бота
MAX_MESSAGE_LENGTH = 4096  # Лимит Telegram
QR_CODE_TIMEOUT = 30  # Секунд для поиска недавно созданных QR-кодов
QR_CODES_DIR = "temp_qr_codes"  # Директория для временных QR-кодов

# Устанавливаем переменную окружения для agent/tools.py
os.environ["QR_CODES_DIR"] = QR_CODES_DIR

# Проверка обязательных переменных
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не найден в переменных окружения!")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY не найден в переменных окружения!")

