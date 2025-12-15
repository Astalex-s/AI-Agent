"""
Настройка логирования для AI-агента
"""
import logging
import os
from datetime import datetime
from pathlib import Path


def setup_logger(name: str = "ai_agent", log_level: str = "INFO") -> logging.Logger:
    """
    Настройка логгера с записью в файл и консоль
    
    Args:
        name: Имя логгера
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        Настроенный логгер
    """
    logger = logging.getLogger(name)
    
    # Устанавливаем уровень логирования
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)
    
    # Избегаем дублирования логов
    if logger.handlers:
        return logger
    
    # Формат логов
    log_format = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # Создаем директорию для логов, если её нет
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # Имя файла лога с датой
    log_filename = log_dir / f"agent_{datetime.now().strftime('%Y%m%d')}.log"
    
    # Обработчик для файла
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setLevel(level)
    file_formatter = logging.Formatter(log_format, date_format)
    file_handler.setFormatter(file_formatter)
    
    # Обработчик для консоли - отключен (логи только в файл)
    # console_handler = logging.StreamHandler()
    # console_handler.setLevel(level)
    # console_formatter = logging.Formatter(
    #     "%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    #     date_format
    # )
    # console_handler.setFormatter(console_formatter)
    
    # Добавляем обработчики (только файл)
    logger.addHandler(file_handler)
    # logger.addHandler(console_handler)  # Отключено - логи только в файл
    
    return logger


def get_logger(name: str = None) -> logging.Logger:
    """
    Получить логгер (создает новый, если не существует)
    
    Args:
        name: Имя логгера (по умолчанию 'ai_agent')
        
    Returns:
        Логгер
    """
    if name is None:
        name = "ai_agent"
    
    logger = logging.getLogger(name)
    
    # Если логгер еще не настроен, настраиваем его
    if not logger.handlers:
        log_level = os.getenv("LOG_LEVEL", "INFO")
        return setup_logger(name, log_level)
    
    return logger

