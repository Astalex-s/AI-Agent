"""
Обработчики команд бота
"""
import logging
from telebot import types

from bot.messages.texts import (
    WELCOME_MESSAGE,
    HELP_MESSAGE,
    CLEAR_SUCCESS,
    CLEAR_ERROR,
    STATUS_TEMPLATE
)
from bot.keyboards.inline import get_main_keyboard

logger = logging.getLogger(__name__)


class CommandHandlers:
    """Обработчики команд бота"""
    
    def __init__(self, bot, agent):
        """
        Инициализация обработчиков команд
        
        Args:
            bot: Экземпляр TeleBot
            agent: Экземпляр AIAgent
        """
        self.bot = bot
        self.agent = agent
        self._register_handlers()
    
    def _register_handlers(self):
        """Регистрация обработчиков команд"""
        
        @self.bot.message_handler(commands=['start', 'help'])
        def handle_start_help(message: types.Message):
            """Обработка команд /start и /help"""
            command = message.text.split()[0]
            
            if command == '/start':
                text = WELCOME_MESSAGE
                keyboard = get_main_keyboard()
                self.bot.reply_to(message, text, reply_markup=keyboard)
            else:
                text = HELP_MESSAGE
                self.bot.reply_to(message, text)
            
            logger.info(f"Пользователь {message.from_user.id} использовал команду {command}")
        
        @self.bot.message_handler(commands=['clear'])
        def handle_clear(message: types.Message):
            """Очистка истории диалога"""
            try:
                self.agent.memory.clear()
                self.agent._save_memory()
                self.bot.reply_to(message, CLEAR_SUCCESS)
                logger.info(f"Пользователь {message.from_user.id} очистил историю")
            except Exception as e:
                error_msg = CLEAR_ERROR.format(error=str(e))
                logger.error(f"Ошибка очистки истории: {e}", exc_info=True)
                self.bot.reply_to(message, error_msg)
        
        @self.bot.message_handler(commands=['status'])
        def handle_status(message: types.Message):
            """Показать статус бота"""
            # Получаем имя модели
            model_name = "gpt-4"
            if hasattr(self.agent.llm, 'model_name'):
                model_name = self.agent.llm.model_name
            elif hasattr(self.agent.llm, 'model'):
                model_name = self.agent.llm.model
            
            # Получаем количество инструментов
            tools_count = len(self.agent.tools)
            
            status_text = STATUS_TEMPLATE.format(
                model=model_name,
                tools_count=tools_count
            )
            
            self.bot.reply_to(message, status_text)
            logger.info(f"Пользователь {message.from_user.id} запросил статус")

