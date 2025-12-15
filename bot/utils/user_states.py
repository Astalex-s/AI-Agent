"""
Управление состояниями пользователей для обработки кнопок
"""
from typing import Dict, Optional

# Словарь для хранения состояний пользователей
# Ключ: user_id, Значение: состояние (например, "waiting_weather_city")
user_states: Dict[int, str] = {}


def set_user_state(user_id: int, state: Optional[str]):
    """
    Установить состояние пользователя
    
    Args:
        user_id: ID пользователя
        state: Состояние (None для очистки)
    """
    if state is None:
        user_states.pop(user_id, None)
    else:
        user_states[user_id] = state


def get_user_state(user_id: int) -> Optional[str]:
    """
    Получить состояние пользователя
    
    Args:
        user_id: ID пользователя
        
    Returns:
        Состояние пользователя или None
    """
    return user_states.get(user_id)


def clear_user_state(user_id: int):
    """
    Очистить состояние пользователя
    
    Args:
        user_id: ID пользователя
    """
    set_user_state(user_id, None)

