"""
Главный файл Telegram бота
"""
import os
import sys
import logging

# Добавляем путь к модулю agent
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telebot import TeleBot

from bot.config import TELEGRAM_BOT_TOKEN, AI_MODEL, AI_TEMPERATURE, QR_CODES_DIR
from agent.agent import AIAgent
from agent.logger_config import get_logger
from bot.handlers.commands import CommandHandlers
from bot.handlers.messages import MessageHandlers

# Инициализация логгера
logger = get_logger("telegram_bot")

# Создаем директорию для QR-кодов при запуске
os.makedirs(QR_CODES_DIR, exist_ok=True)
logger.info(f"Директория для QR-кодов создана/проверена: {QR_CODES_DIR}")


class TelegramAIAgent:
    """Telegram бот для AI-агента"""
    
    def __init__(self):
        """Инициализация Telegram бота"""
        # Инициализация Telegram бота
        self.bot = TeleBot(TELEGRAM_BOT_TOKEN)
        logger.info("Telegram бот инициализирован")
        
        # Инициализация AI-агента
        logger.info("Инициализация AI-агента...")
        self.agent = AIAgent(model=AI_MODEL, temperature=AI_TEMPERATURE)
        logger.info("AI-агент успешно инициализирован")
        
        # Регистрация обработчиков
        self.command_handlers = CommandHandlers(self.bot, self.agent)
        self.message_handlers = MessageHandlers(self.bot, self.agent)
        logger.info("Обработчики зарегистрированы")
    
    def start_polling(self):
        """Запуск бота в режиме polling"""
        logger.info("Запуск Telegram бота в режиме polling...")
        try:
            self.bot.infinity_polling(timeout=10, long_polling_timeout=5)
        except Exception as e:
            logger.error(f"Ошибка при запуске бота: {e}", exc_info=True)
            raise


def main():
    """Главная функция для запуска Telegram бота"""
    try:
        # Инициализация бота
        bot = TelegramAIAgent()
        
        print("=" * 60)
        print("🤖 Telegram AI-Агент запущен!")
        print("=" * 60)
        print("Бот готов к работе. Ожидание сообщений...")
        print("Для остановки нажмите Ctrl+C")
        print("-" * 60)
        
        # Запуск бота
        bot.start_polling()
        
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
        print("\n👋 Бот остановлен. До свидания!")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        print(f"\n❌ Критическая ошибка: {e}")


if __name__ == "__main__":
    main()

