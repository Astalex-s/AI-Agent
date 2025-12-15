"""
Обработчики текстовых сообщений бота
"""
import os
import logging
from telebot import types

from bot.utils.qr_extractor import extract_qr_file_path
from bot.utils.message_splitter import split_message
from bot.utils.user_states import get_user_state, set_user_state, clear_user_state
from bot.messages.texts import (
    ERROR_MESSAGE,
    QR_CODE_NOT_FOUND,
    QR_CODE_SEND_ERROR,
    QR_CODE_FILE_ERROR,
    WEATHER_CITY_REQUEST,
    CRYPTO_REQUEST,
    CURRENCY_REQUEST,
    SEARCH_REQUEST,
    QR_CODE_REQUEST,
    HELP_MESSAGE,
    STATUS_TEMPLATE
)

logger = logging.getLogger(__name__)


class MessageHandlers:
    """Обработчики текстовых сообщений"""
    
    def __init__(self, bot, agent):
        """
        Инициализация обработчиков сообщений
        
        Args:
            bot: Экземпляр TeleBot
            agent: Экземпляр AIAgent
        """
        self.bot = bot
        self.agent = agent
        self._register_handlers()
    
    def _register_handlers(self):
        """Регистрация обработчиков сообщений"""
        
        @self.bot.message_handler(func=lambda message: True)
        def handle_message(message: types.Message):
            """Обработка всех текстовых сообщений"""
            user_id = message.from_user.id
            username = message.from_user.username or message.from_user.first_name or "Unknown"
            user_input = message.text
            
            logger.info(f"Получено сообщение от пользователя {user_id} ({username}): {user_input[:50]}...")
            
            # Проверяем состояние пользователя (ожидание дополнительной информации)
            user_state = get_user_state(user_id)
            
            if user_state:
                # Пользователь находится в состоянии ожидания информации
                self._handle_state_message(message, user_id, user_input, user_state)
                return
            
            # Проверяем, является ли сообщение нажатием кнопки
            if self._handle_button_press(message, user_id, user_input):
                return
            
            # Обычная обработка сообщения через AI-агента
            self._handle_regular_message(message, user_id, user_input)
    
    def _handle_state_message(self, message: types.Message, user_id: int, user_input: str, state: str):
        """Обработка сообщения в состоянии ожидания информации"""
        # Формируем запрос для AI-агента на основе состояния
        if state == "waiting_weather_city":
            query = f"Какая погода в городе {user_input}?"
        elif state == "waiting_crypto":
            query = f"Сколько стоит {user_input}?"
        elif state == "waiting_currency":
            query = f"Какой курс валют {user_input}?"
        elif state == "waiting_search":
            query = f"Найди информацию о {user_input}"
        elif state == "waiting_qr_code":
            query = f"Создай QR-код для {user_input}"
        else:
            query = user_input
        
        # Очищаем состояние
        clear_user_state(user_id)
        
        # Обрабатываем запрос
        self._process_agent_request(message, user_id, query)
    
    def _handle_button_press(self, message: types.Message, user_id: int, user_input: str) -> bool:
        """Обработка нажатия кнопки"""
        button_text = user_input.strip()
        
        if button_text == "🌤️ Погода":
            set_user_state(user_id, "waiting_weather_city")
            self.bot.reply_to(message, WEATHER_CITY_REQUEST)
            logger.info(f"Пользователь {user_id} нажал кнопку 'Погода'")
            return True
        
        elif button_text == "💰 Криптовалюта":
            set_user_state(user_id, "waiting_crypto")
            self.bot.reply_to(message, CRYPTO_REQUEST)
            logger.info(f"Пользователь {user_id} нажал кнопку 'Криптовалюта'")
            return True
        
        elif button_text == "💵 Валюта":
            set_user_state(user_id, "waiting_currency")
            self.bot.reply_to(message, CURRENCY_REQUEST)
            logger.info(f"Пользователь {user_id} нажал кнопку 'Валюта'")
            return True
        
        elif button_text == "🔍 Поиск":
            set_user_state(user_id, "waiting_search")
            self.bot.reply_to(message, SEARCH_REQUEST)
            logger.info(f"Пользователь {user_id} нажал кнопку 'Поиск'")
            return True
        
        elif button_text == "📱 QR-код":
            set_user_state(user_id, "waiting_qr_code")
            self.bot.reply_to(message, QR_CODE_REQUEST)
            logger.info(f"Пользователь {user_id} нажал кнопку 'QR-код'")
            return True
        
        elif button_text == "❓ Помощь":
            self.bot.reply_to(message, HELP_MESSAGE)
            logger.info(f"Пользователь {user_id} нажал кнопку 'Помощь'")
            return True
        
        elif button_text == "📊 Статус":
            # Обработка статуса
            model_name = "gpt-4"
            if hasattr(self.agent.llm, 'model_name'):
                model_name = self.agent.llm.model_name
            elif hasattr(self.agent.llm, 'model'):
                model_name = self.agent.llm.model
            
            status_text = STATUS_TEMPLATE.format(
                model=model_name,
                tools_count=len(self.agent.tools)
            )
            self.bot.reply_to(message, status_text)
            logger.info(f"Пользователь {user_id} нажал кнопку 'Статус'")
            return True
        
        return False
    
    def _handle_regular_message(self, message: types.Message, user_id: int, user_input: str):
        """Обработка обычного сообщения через AI-агента"""
        self._process_agent_request(message, user_id, user_input)
    
    def _process_agent_request(self, message: types.Message, user_id: int, query: str):
        """Обработка запроса через AI-агента"""
        # Показываем, что бот печатает
        self.bot.send_chat_action(message.chat.id, 'typing')
        
        try:
            # Обработка запроса через AI-агента
            logger.debug(f"Обработка запроса через AI-агента: {query[:50]}...")
            response = self.agent.process(query)
            logger.info(f"Ответ агента получен (длина: {len(response)} символов)")
            
            # Проверяем, был ли создан QR-код
            qr_file_path = extract_qr_file_path(response)
            if qr_file_path and os.path.exists(qr_file_path):
                # Отправляем QR-код как изображение
                logger.info(f"Отправка QR-кода: {qr_file_path}")
                try:
                    self.bot.send_chat_action(message.chat.id, 'upload_photo')
                    with open(qr_file_path, 'rb') as photo:
                        # Отправляем фото с кратким сообщением об успешной генерации
                        caption = response if len(response) <= 1024 else response[:1024]
                        self.bot.send_photo(message.chat.id, photo, caption=caption)
                    logger.info(f"QR-код отправлен пользователю {user_id}")
                    
                    # Удаляем файл после отправки
                    try:
                        os.remove(qr_file_path)
                        logger.info(f"QR-код файл {qr_file_path} удален")
                    except Exception as rm_error:
                        logger.warning(f"Не удалось удалить QR-код файл: {rm_error}")
                except Exception as photo_error:
                    logger.error(f"Ошибка отправки фото: {photo_error}", exc_info=True)
                    # Если не удалось отправить фото, отправляем текстовый ответ
                    error_msg = QR_CODE_FILE_ERROR.format(
                        response=response,
                        file_path=qr_file_path
                    )
                    self.bot.reply_to(message, error_msg)
            else:
                # Отправляем обычный текстовый ответ
                message_parts = split_message(response)
                for i, part in enumerate(message_parts):
                    if i == 0:
                        self.bot.reply_to(message, part)
                    else:
                        self.bot.send_message(message.chat.id, part)
                
                logger.info(f"Ответ отправлен пользователю {user_id}")
            
        except Exception as e:
            error_msg = ERROR_MESSAGE.format(error=str(e))
            logger.error(f"Ошибка обработки сообщения от {user_id}: {e}", exc_info=True)
            self.bot.reply_to(message, error_msg)
