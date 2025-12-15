"""
Утилита для разбиения длинных сообщений
"""
from bot.config import MAX_MESSAGE_LENGTH


def split_message(text: str, max_length: int = MAX_MESSAGE_LENGTH) -> list:
    """
    Разбивает длинное сообщение на части
    
    Args:
        text: Текст сообщения
        max_length: Максимальная длина одной части
        
    Returns:
        Список частей сообщения
    """
    if len(text) <= max_length:
        return [text]
    
    parts = []
    current_pos = 0
    
    while current_pos < len(text):
        # Берем кусок текста
        chunk = text[current_pos:current_pos + max_length]
        
        # Если это не последний кусок, пытаемся разбить по переносу строки
        if current_pos + max_length < len(text):
            last_newline = chunk.rfind('\n')
            if last_newline > max_length * 0.5:  # Если перенос строки не слишком близко к началу
                chunk = chunk[:last_newline + 1]
                current_pos += last_newline + 1
            else:
                # Разбиваем по пробелу
                last_space = chunk.rfind(' ')
                if last_space > max_length * 0.5:
                    chunk = chunk[:last_space]
                    current_pos += last_space + 1
                else:
                    current_pos += max_length
        else:
            current_pos = len(text)
        
        parts.append(chunk)
    
    return parts

