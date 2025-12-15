"""
Инструменты для AI-агента
"""
import json
import os
import subprocess
import requests
from typing import Optional, Dict, Any
from langchain.tools import Tool
from duckduckgo_search import DDGS
from geopy.geocoders import Nominatim
from .logger_config import get_logger

# Импорт для QR-кодов (опционально, если библиотека установлена)
try:
    import qrcode
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False

# Инициализация логгера для инструментов
logger = get_logger("ai_agent.tools")


def _normalize_input(value) -> str:
    """
    Нормализация входных данных - преобразование списка в строку
    
    Args:
        value: Входное значение (может быть строкой или списком)
        
    Returns:
        Строка
    """
    if isinstance(value, list):
        # Если список, фильтруем словари (метаданные) и берем реальные аргументы
        real_args = [v for v in value if not isinstance(v, dict)]
        if not real_args:
            # Если только словари, берем первый элемент
            if len(value) == 1:
                return str(value[0])
            return ' '.join(str(v) for v in value)
        # Берем первый реальный аргумент или объединяем все
        if len(real_args) == 1:
            return str(real_args[0])
        return ' '.join(str(v) for v in real_args)
    return str(value)


def _extract_tool_args(*args, **kwargs):
    """
    Извлечение реальных аргументов из вызова инструмента LangChain
    
    LangChain может передавать метаданные в виде словаря вместе с аргументами.
    Эта функция фильтрует словари и возвращает только реальные аргументы.
    
    Args:
        *args: Позиционные аргументы
        **kwargs: Именованные аргументы
        
    Returns:
        Кортеж (реальные позиционные аргументы, реальные именованные аргументы)
    """
    # Фильтруем словари из позиционных аргументов (это метаданные)
    real_args = [arg for arg in args if not isinstance(arg, dict)]
    
    # Фильтруем словари из именованных аргументов
    real_kwargs = {k: v for k, v in kwargs.items() if not isinstance(v, dict)}
    
    return real_args, real_kwargs


def web_search(*args, **kwargs) -> str:
    """
    Поиск информации в интернете через DuckDuckGo
    
    Args:
        *args: Позиционные аргументы (может включать метаданные LangChain)
        **kwargs: Именованные аргументы
        
    Returns:
        Строка с результатами поиска
    """
    # Извлекаем реальные аргументы
    real_args, _ = _extract_tool_args(*args, **kwargs)
    
    query = real_args[0] if real_args else (kwargs.get('query', args[0] if args else ""))
    
    # Нормализация входных данных
    query = _normalize_input(query)
    logger.info(f"Выполнение веб-поиска: {query}")
    try:
        logger.debug("Инициализация DuckDuckGo поиска...")
        with DDGS() as ddgs:
            logger.debug(f"Поиск по запросу: {query}")
            results = list(ddgs.text(query, max_results=5))
            logger.debug(f"Получено результатов: {len(results)}")
            
            if not results:
                logger.warning("Результаты поиска не найдены")
                return "Результаты поиска не найдены."
            
            formatted_results = []
            for i, result in enumerate(results, 1):
                logger.debug(f"Обработка результата {i}/{len(results)}")
                formatted_results.append(
                    f"Заголовок: {result.get('title', 'N/A')}\n"
                    f"URL: {result.get('href', 'N/A')}\n"
                    f"Описание: {result.get('body', 'N/A')}\n"
                )
            
            result_str = "\n---\n".join(formatted_results)
            logger.info(f"Поиск завершен успешно, найдено {len(results)} результатов")
            return result_str
    except Exception as e:
        logger.error(f"Ошибка при веб-поиске: {e}", exc_info=True)
        return f"Ошибка при поиске: {str(e)}"


def http_request(*args, **kwargs) -> str:
    """
    Выполнение HTTP запросов
    
    Args:
        *args: Позиционные аргументы (может включать метаданные LangChain)
        **kwargs: Именованные аргументы
        
    Returns:
        Ответ сервера в виде строки
    """
    # Извлекаем реальные аргументы
    real_args, _ = _extract_tool_args(*args, **kwargs)
    
    request_str = real_args[0] if real_args else (kwargs.get('request_str', args[0] if args else ""))
    
    # Нормализация входных данных
    if isinstance(request_str, list):
        # Если список, объединяем через |
        request_str = '|'.join(str(v) for v in request_str)
    else:
        request_str = str(request_str)
    
    logger.info(f"Выполнение HTTP запроса: {request_str[:100]}...")
    try:
        parts = request_str.split('|')
        method = parts[0].strip().upper() if len(parts) > 0 else "GET"
        url = parts[1].strip() if len(parts) > 1 else ""
        headers_str = parts[2].strip() if len(parts) > 2 else None
        data_str = parts[3].strip() if len(parts) > 3 else None
        
        logger.debug(f"Парсинг запроса: method={method}, url={url}")
        
        if not url:
            logger.error("URL не указан")
            return "Ошибка: URL обязателен. Формат: 'method|url|headers_json|data_json'"
        
        headers_dict = {}
        data_dict = None
        
        if headers_str:
            try:
                headers_dict = json.loads(headers_str)
                logger.debug(f"Заголовки загружены: {len(headers_dict)} элементов")
            except Exception as e:
                logger.error(f"Ошибка парсинга headers JSON: {e}")
                return f"Ошибка: Неверный формат JSON для headers: {headers_str}"
        
        if data_str:
            try:
                data_dict = json.loads(data_str)
                logger.debug(f"Данные загружены: {len(data_dict)} элементов")
            except Exception as e:
                logger.error(f"Ошибка парсинга data JSON: {e}")
                return f"Ошибка: Неверный формат JSON для data: {data_str}"
        
        logger.info(f"Выполнение {method} запроса к {url}")
        if method == "GET":
            response = requests.get(url, headers=headers_dict)
        elif method == "POST":
            response = requests.post(url, headers=headers_dict, json=data_dict)
        elif method == "PUT":
            response = requests.put(url, headers=headers_dict, json=data_dict)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers_dict)
        else:
            logger.error(f"Неподдерживаемый метод: {method}")
            return f"Неподдерживаемый метод: {method}"
        
        logger.debug(f"Получен ответ: статус {response.status_code}")
        response.raise_for_status()
        result = f"Status: {response.status_code}\nResponse: {response.text[:1000]}"
        logger.info(f"HTTP запрос выполнен успешно: статус {response.status_code}")
        return result
    except Exception as e:
        logger.error(f"Ошибка HTTP запроса: {e}", exc_info=True)
        return f"Ошибка HTTP запроса: {str(e)}"


def read_file(*args, **kwargs) -> str:
    """
    Чтение файла
    
    Args:
        *args: Позиционные аргументы (может включать метаданные LangChain)
        **kwargs: Именованные аргументы
        
    Returns:
        Содержимое файла
    """
    # Извлекаем реальные аргументы, игнорируя метаданные
    real_args, _ = _extract_tool_args(*args, **kwargs)
    
    # Берем первый аргумент или используем значение из kwargs
    if real_args:
        file_path = real_args[0]
    elif 'file_path' in kwargs:
        file_path = kwargs['file_path']
    else:
        # Если аргументы переданы как список в args
        file_path = args[0] if args else ""
    
    # Нормализация входных данных
    file_path = _normalize_input(file_path)
    
    # Исправление пути: если начинается с '/', но это не абсолютный путь в Windows
    original_path = file_path
    if file_path.startswith('/'):
        # В Windows путь вида '/file.txt' не является абсолютным (абсолютный был бы 'C:\file.txt')
        # Убираем начальный '/' для относительных путей
        if os.name == 'nt':  # Windows
            file_path = file_path.lstrip('/')
            logger.debug(f"Исправлен путь для Windows: '{original_path}' -> '{file_path}'")
        else:
            # В Linux/Mac путь вида '/file.txt' является абсолютным
            # Но если файл не существует, пробуем как относительный
            if not os.path.exists(file_path) and len(file_path) > 1:
                relative_path = file_path.lstrip('/')
                if os.path.exists(relative_path):
                    file_path = relative_path
                    logger.debug(f"Файл найден по относительному пути: '{file_path}'")
    
    logger.info(f"Чтение файла: {file_path}")
    try:
        logger.debug(f"Открытие файла {file_path}...")
        
        # Проверяем существование файла
        if not os.path.exists(file_path):
            # Если файл не найден, пробуем варианты
            logger.warning(f"Файл '{file_path}' не найден, пробуем варианты...")
            
            # Вариант 1: пробуем с убранным начальным '/'
            if file_path.startswith('/'):
                alt_path = file_path.lstrip('/')
                if os.path.exists(alt_path):
                    file_path = alt_path
                    logger.info(f"Файл найден по альтернативному пути: {file_path}")
                else:
                    error_msg = f"Файл '{original_path}' не найден. Проверьте правильность пути."
                    logger.error(error_msg)
                    return f"Ошибка чтения файла: {error_msg}"
            else:
                error_msg = f"Файл '{file_path}' не найден. Проверьте правильность пути."
                logger.error(error_msg)
                return f"Ошибка чтения файла: {error_msg}"
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        logger.info(f"Файл прочитан успешно, размер: {len(content)} символов")
        logger.debug(f"Первые 100 символов: {content[:100]}...")
        return content
    except FileNotFoundError:
        error_msg = f"Файл '{file_path}' не найден. Убедитесь, что путь указан правильно."
        logger.error(error_msg)
        return f"Ошибка чтения файла: {error_msg}"
    except Exception as e:
        logger.error(f"Ошибка чтения файла {file_path}: {e}", exc_info=True)
        return f"Ошибка чтения файла: {str(e)}"


def write_file_wrapper(*args, **kwargs):
    """
    Обертка для write_file, которая правильно обрабатывает аргументы от LangChain
    """
    logger.debug(f"write_file_wrapper вызван с args={args}, kwargs={kwargs}")
    
    # Извлекаем реальные аргументы, игнорируя метаданные
    real_args, _ = _extract_tool_args(*args, **kwargs)
    
    # Получаем аргумент
    if real_args:
        file_path_and_content = real_args[0]
    elif args:
        # Если real_args пустой, но args есть, фильтруем словари
        non_dict_args = [a for a in args if not isinstance(a, dict)]
        file_path_and_content = non_dict_args[0] if non_dict_args else (args[0] if args else "")
    else:
        file_path_and_content = kwargs.get('file_path_and_content', "")
    
    logger.info(f"write_file вызван с аргументом: {file_path_and_content}, тип: {type(file_path_and_content)}")
    
    return write_file_impl(file_path_and_content)


def write_file_impl(file_path_and_content) -> str:
    """
    Реализация записи в файл
    
    Args:
        file_path_and_content: Строка в формате "путь_к_файлу|содержимое" или список
        
    Returns:
        Результат операции
    """
    # Нормализация входных данных
    if isinstance(file_path_and_content, list):
        # Фильтруем словари (метаданные LangChain)
        filtered = [v for v in file_path_and_content if not isinstance(v, dict)]
        if len(filtered) >= 2:
            file_path_and_content = f"{filtered[0]}|{filtered[1]}"
        elif len(filtered) == 1:
            file_path_and_content = str(filtered[0])
        else:
            file_path_and_content = str(file_path_and_content[0]) if file_path_and_content else ""
    else:
        file_path_and_content = str(file_path_and_content)
    
    logger.debug(f"Нормализованный аргумент: {file_path_and_content[:100]}...")
    
    try:
        # Разделяем путь и содержимое по символу |
        if '|' in file_path_and_content:
            parts = file_path_and_content.split('|', 1)
            file_path = parts[0].strip()
            content = parts[1].strip() if len(parts) > 1 else ""
        else:
            # Если нет разделителя, это только путь (создаем пустой файл)
            logger.warning(f"Нет разделителя | в '{file_path_and_content}', будет создан пустой файл")
            file_path = file_path_and_content.strip()
            content = ""
        
        if not file_path:
            logger.error("Путь к файлу не указан")
            return "Ошибка: Не указан путь к файлу"
        
        logger.info(f"Запись в файл: {file_path}, размер содержимого: {len(content)} символов")
        
        # Создаем директорию, если нужно
        dir_path = os.path.dirname(file_path) if os.path.dirname(file_path) else '.'
        if dir_path != '.':
            logger.debug(f"Создание директории: {dir_path}")
            os.makedirs(dir_path, exist_ok=True)
        
        # Записываем файл
        logger.debug(f"Открытие файла {file_path} для записи...")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"✅ Файл {file_path} успешно записан ({len(content)} символов)")
        return f"Файл {file_path} успешно записан ({len(content)} символов)."
    except Exception as e:
        logger.error(f"❌ Ошибка записи файла: {e}", exc_info=True)
        return f"Ошибка записи файла: {str(e)}"


def write_file(file_path_and_content: str) -> str:
    """
    Запись в файл (публичный интерфейс для LangChain)
    
    Args:
        file_path_and_content: Строка в формате "путь_к_файлу|содержимое"
        
    Returns:
        Результат операции
    """
    return write_file_wrapper(file_path_and_content)


def execute_terminal(*args, **kwargs) -> str:
    """
    Безопасное выполнение терминальных команд
    
    Args:
        *args: Позиционные аргументы (может включать метаданные LangChain)
        **kwargs: Именованные аргументы
        
    Returns:
        Вывод команды
    """
    # Извлекаем реальные аргументы
    real_args, _ = _extract_tool_args(*args, **kwargs)
    
    command = real_args[0] if real_args else (kwargs.get('command', args[0] if args else ""))
    
    # Нормализация входных данных
    command = _normalize_input(command)
    logger.info(f"Выполнение терминальной команды: {command}")
    
    # Список запрещенных команд для безопасности
    dangerous_commands = ['rm', 'del', 'format', 'mkfs', 'dd', 'shutdown', 'reboot']
    command_lower = command.lower().strip()
    
    for dangerous in dangerous_commands:
        if command_lower.startswith(dangerous):
            logger.warning(f"Попытка выполнить запрещенную команду: {dangerous}")
            return f"Ошибка: Команда '{dangerous}' запрещена из соображений безопасности."
    
    try:
        logger.debug(f"Запуск команды через subprocess...")
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            encoding='utf-8'
        )
        
        logger.debug(f"Команда выполнена, exit code: {result.returncode}")
        output = result.stdout if result.stdout else result.stderr
        logger.info(f"Команда выполнена успешно, вывод: {len(output)} символов")
        logger.debug(f"Вывод команды: {output[:200]}...")
        return f"Exit code: {result.returncode}\nOutput:\n{output}"
    except subprocess.TimeoutExpired:
        logger.error("Команда превысила лимит времени (30 секунд)")
        return "Ошибка: Команда превысила лимит времени (30 секунд)."
    except Exception as e:
        logger.error(f"Ошибка выполнения команды: {e}", exc_info=True)
        return f"Ошибка выполнения команды: {str(e)}"


def get_weather(*args, **kwargs) -> str:
    """
    Получение текущей погоды для города
    
    Args:
        *args: Позиционные аргументы (может включать метаданные LangChain)
        **kwargs: Именованные аргументы
        
    Returns:
        Информация о погоде
    """
    # Извлекаем реальные аргументы
    real_args, _ = _extract_tool_args(*args, **kwargs)
    
    city = real_args[0] if real_args else (kwargs.get('city', args[0] if args else ""))
    
    # Нормализация входных данных
    city = _normalize_input(city)
    logger.info(f"Получение погоды для города: {city}")
    try:
        # Геокодирование: преобразование названия города в координаты
        logger.debug(f"Геокодирование города {city}...")
        # Увеличиваем таймаут для geopy (по умолчанию 1 секунда слишком мало)
        geolocator = Nominatim(user_agent="ai_agent", timeout=10)
        
        # Пробуем геокодирование с повторными попытками
        location = None
        max_retries = 3
        for attempt in range(max_retries):
            try:
                location = geolocator.geocode(city, timeout=10)
                if location:
                    break
            except Exception as geocode_error:
                logger.warning(f"Попытка {attempt + 1}/{max_retries} геокодирования не удалась: {geocode_error}")
                if attempt == max_retries - 1:
                    raise
                import time
                time.sleep(1)  # Небольшая задержка перед повторной попыткой
        
        if not location:
            logger.warning(f"Город '{city}' не найден при геокодировании")
            return f"Город '{city}' не найден."
        
        lat = location.latitude
        lon = location.longitude
        logger.info(f"Координаты города {city}: lat={lat}, lon={lon}")
        
        # Запрос погоды через Open-Meteo API с увеличенным таймаутом
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        logger.debug(f"Запрос погоды: {url}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        logger.debug("Данные о погоде получены")
        
        if 'current_weather' not in data:
            logger.warning("В ответе API нет данных current_weather")
            return "Данные о погоде не получены."
        
        weather = data['current_weather']
        temperature = weather.get('temperature', 'N/A')
        windspeed = weather.get('windspeed', 'N/A')
        weathercode = weather.get('weathercode', 'N/A')
        logger.debug(f"Погода: temp={temperature}°C, wind={windspeed} км/ч, code={weathercode}")
        
        # Простое преобразование weathercode в описание
        weather_descriptions = {
            0: "Ясно",
            1: "Преимущественно ясно",
            2: "Переменная облачность",
            3: "Пасмурно",
            45: "Туман",
            48: "Изморозь",
            51: "Легкая морось",
            53: "Умеренная морось",
            55: "Сильная морось",
            61: "Легкий дождь",
            63: "Умеренный дождь",
            65: "Сильный дождь",
            71: "Легкий снег",
            73: "Умеренный снег",
            75: "Сильный снег",
            80: "Легкий ливень",
            81: "Умеренный ливень",
            82: "Сильный ливень",
            85: "Снегопад",
            86: "Сильный снегопад",
            95: "Гроза",
            96: "Гроза с градом",
            99: "Сильная гроза с градом"
        }
        
        condition = weather_descriptions.get(weathercode, f"Код: {weathercode}")
        
        result = (
            f"Погода в {city}:\n"
            f"Температура: {temperature}°C\n"
            f"Ветер: {windspeed} км/ч\n"
            f"Условия: {condition}"
        )
        logger.info(f"Погода получена успешно для {city}")
        return result
    except Exception as e:
        error_str = str(e)
        logger.error(f"Ошибка получения погоды для {city}: {e}", exc_info=True)
        
        # Специальная обработка ошибок таймаута и недоступности сервиса
        if "timeout" in error_str.lower() or "timed out" in error_str.lower():
            return (
                f"Ошибка: Сервис геокодирования недоступен (таймаут). "
                f"Попробуйте позже или укажите более точное название города."
            )
        elif "GeocoderUnavailable" in error_str or "unavailable" in error_str.lower():
            return (
                f"Ошибка: Сервис геокодирования временно недоступен. "
                f"Попробуйте позже."
            )
        elif "not found" in error_str.lower() or location is None:
            return f"Город '{city}' не найден. Проверьте правильность написания названия города."
        else:
            return f"Ошибка получения погоды для {city}: {str(e)}"


def get_crypto_price(*args, **kwargs) -> str:
    """
    Получение курса криптовалюты
    
    Args:
        *args: Позиционные аргументы (может включать метаданные LangChain)
        **kwargs: Именованные аргументы
        
    Returns:
        Цена криптовалюты
    """
    # Извлекаем реальные аргументы
    real_args, _ = _extract_tool_args(*args, **kwargs)
    
    coin_and_currency = real_args[0] if real_args else (kwargs.get('coin_and_currency', args[0] if args else ""))
    
    # Обработка входных данных - если список, объединяем через запятую
    if isinstance(coin_and_currency, list):
        if len(coin_and_currency) == 1:
            coin_and_currency = str(coin_and_currency[0])
        elif len(coin_and_currency) == 2:
            coin_and_currency = f"{coin_and_currency[0]},{coin_and_currency[1]}"
        else:
            coin_and_currency = str(coin_and_currency[0])
    else:
        coin_and_currency = str(coin_and_currency)
    
    logger.info(f"Получение курса криптовалюты: {coin_and_currency}")
    try:
        parts = coin_and_currency.split(',')
        coin = parts[0].strip().lower()
        currency = parts[1].strip().lower() if len(parts) > 1 else "usd"
        
        logger.debug(f"Парсинг: coin={coin}, currency={currency}")
        
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies={currency}"
        logger.debug(f"Запрос к CoinGecko API: {url}")
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        logger.debug(f"Ответ API получен: {data}")
        
        if coin not in data:
            logger.warning(f"Криптовалюта '{coin}' не найдена в ответе API")
            return f"Криптовалюта '{coin}' не найдена. Попробуйте: bitcoin, ethereum, etc."
        
        price = data[coin].get(currency)
        if price is None:
            logger.warning(f"Валюта '{currency}' не поддерживается для {coin}")
            return f"Валюта '{currency}' не поддерживается."
        
        result = f"Цена {coin.upper()}: {price:,.2f} {currency.upper()}"
        logger.info(f"Курс получен успешно: {result}")
        return result
    except Exception as e:
        logger.error(f"Ошибка получения курса криптовалюты: {e}", exc_info=True)
        return f"Ошибка получения курса: {str(e)}"


def get_currency_rate(*args, **kwargs) -> str:
    """
    Получение курса валют (EUR, USD, RUB и др.)
    
    Args:
        *args: Позиционные аргументы (может включать метаданные LangChain)
        **kwargs: Именованные аргументы
        
    Returns:
        Курс валюты
    """
    real_args, _ = _extract_tool_args(*args, **kwargs)
    currency_pair = real_args[0] if real_args else (kwargs.get('currency_pair', args[0] if args else ""))
    
    # Нормализация входных данных
    currency_pair = _normalize_input(currency_pair)
    logger.info(f"Получение курса валют: {currency_pair}")
    
    try:
        # Парсим пару валют (например: "USD/EUR" или "USD to EUR" или "USD EUR")
        parts = currency_pair.replace('to', '/').replace('TO', '/').replace(' ', '/').split('/')
        if len(parts) >= 2:
            base_currency = parts[0].strip().upper()
            target_currency = parts[1].strip().upper()
        else:
            # Если только одна валюта, используем USD как базовую
            base_currency = "USD"
            target_currency = parts[0].strip().upper()
        
        logger.debug(f"Парсинг: base={base_currency}, target={target_currency}")
        
        # Используем бесплатный API exchangerate-api.com
        url = f"https://api.exchangerate-api.com/v4/latest/{base_currency}"
        logger.debug(f"Запрос к ExchangeRate API: {url}")
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        logger.debug(f"Ответ API получен: rates доступны для {len(data.get('rates', {}))} валют")
        
        rates = data.get('rates', {})
        
        if target_currency not in rates:
            available_currencies = ', '.join(sorted(rates.keys())[:20])  # Показываем первые 20
            logger.warning(f"Валюта '{target_currency}' не найдена в ответе API")
            return (
                f"Валюта '{target_currency}' не найдена.\n"
                f"Доступные валюты (примеры): {available_currencies}..."
            )
        
        rate = rates[target_currency]
        result = f"Курс {base_currency}/{target_currency}: {rate:.4f}"
        logger.info(f"Курс получен успешно: {result}")
        return result
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка запроса к API курсов валют: {e}", exc_info=True)
        return f"Ошибка получения курса валют: {str(e)}"
    except Exception as e:
        logger.error(f"Ошибка получения курса валют: {e}", exc_info=True)
        return f"Ошибка получения курса: {str(e)}"


def generate_qr_code(*args, **kwargs) -> str:
    """
    Генерация QR-кода из текста или URL
    
    Args:
        *args: Позиционные аргументы (может включать метаданные LangChain)
        **kwargs: Именованные аргументы
        
    Returns:
        Результат операции
    """
    if not QRCODE_AVAILABLE:
        logger.error("Библиотека qrcode не установлена")
        return (
            "Ошибка: Библиотека qrcode не установлена. "
            "Установите её командой: pip install qrcode[pil]"
        )
    
    # Извлекаем реальные аргументы
    real_args, _ = _extract_tool_args(*args, **kwargs)
    
    data_and_path = real_args[0] if real_args else (kwargs.get('data_and_path', args[0] if args else ""))
    
    # Обработка входных данных
    if isinstance(data_and_path, list):
        # Фильтруем словари (метаданные LangChain)
        filtered = [v for v in data_and_path if not isinstance(v, dict)]
        if len(filtered) >= 2:
            data_and_path = f"{filtered[0]}|{filtered[1]}"
        elif len(filtered) == 1:
            data_and_path = str(filtered[0])
        else:
            data_and_path = str(data_and_path[0]) if data_and_path else ""
    else:
        data_and_path = str(data_and_path)
    
    logger.info(f"Генерация QR-кода: {data_and_path[:50]}...")
    
    try:
        # Разделяем данные и путь по символу |
        if '|' in data_and_path:
            parts = data_and_path.split('|', 1)
            data = parts[0].strip()
            file_path = parts[1].strip() if len(parts) > 1 else "qr_code.png"
        else:
            # Если нет разделителя, используем данные как текст и стандартное имя файла
            data = data_and_path.strip()
            file_path = "qr_code.png"
        
        if not data:
            logger.error("Данные для QR-кода не указаны")
            return "Ошибка: Не указаны данные для генерации QR-кода"
        
        logger.debug(f"Данные для QR-кода: {data[:100]}..., путь сохранения: {file_path}")
        
        # Исправление пути (убираем начальный / если есть)
        if file_path.startswith('/') and os.name == 'nt':
            file_path = file_path.lstrip('/')
        
        # Используем директорию для QR-кодов из переменной окружения или по умолчанию
        qr_dir = os.getenv("QR_CODES_DIR", "temp_qr_codes")
        
        # Если указан только имя файла без пути, добавляем директорию
        if os.path.dirname(file_path) == '':
            # Создаем директорию, если её нет
            os.makedirs(qr_dir, exist_ok=True)
            file_path = os.path.join(qr_dir, file_path)
        else:
            # Если указан путь, используем его, но создаем директорию если нужно
            dir_path = os.path.dirname(file_path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)
        
        logger.debug(f"Финальный путь сохранения QR-кода: {file_path}")
        
        # Создаем QR-код
        logger.debug("Создание QR-кода...")
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        # Создаем изображение
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Сохраняем изображение
        logger.debug(f"Сохранение QR-кода в файл {file_path}...")
        img.save(file_path)
        
        file_size = os.path.getsize(file_path)
        logger.info(f"✅ QR-код успешно создан: {file_path} ({file_size} байт)")
        # Возвращаем краткое сообщение об успешной генерации
        return f"✅ QR-код успешно создан для: {data[:100]}"
    except Exception as e:
        logger.error(f"Ошибка генерации QR-кода: {e}", exc_info=True)
        return f"Ошибка генерации QR-кода: {str(e)}"


def get_tools():
    """
    Возвращает список всех доступных инструментов для LangChain
    """
    logger.info("Создание списка инструментов для LangChain")
    tools = [
        Tool(
            name="web_search",
            func=web_search,
            description=(
                "Поиск информации в интернете через DuckDuckGo. "
                "Используй для получения актуальной информации, новостей, фактов. "
                "Вход: поисковый запрос (строка)."
            )
        ),
        Tool(
            name="http_request",
            func=http_request,
            description=(
                "Выполнение HTTP запросов (GET, POST, PUT, DELETE). "
                "Используй для взаимодействия с API. "
                "Вход: строка в формате 'method|url|headers_json|data_json' (headers и data опциональны)."
            )
        ),
        Tool(
            name="read_file",
            func=read_file,
            description=(
                "Чтение содержимого файла. "
                "Используй для чтения текстовых файлов (JSON, TXT, MD и т.д.). "
                "Вход: путь к файлу (строка). "
                "Пример: 'test.json' или 'output.txt'. "
                "ВАЖНО: Используй относительный путь без начального слеша, например 'test.json', а не '/test.json'."
            )
        ),
        Tool(
            name="write_file",
            func=write_file_wrapper,
            description=(
                "Запись содержимого в файл. "
                "Используй для создания или изменения файлов. "
                "Вход: строка в формате 'путь_к_файлу|содержимое'. "
                "Пример: 'output.txt|Текст для записи в файл'. "
                "ВАЖНО: Разделяй путь и содержимое символом | (вертикальная черта). "
                "Путь должен быть относительным без начального слеша, например 'output.txt', а не '/output.txt'."
            )
        ),
        Tool(
            name="execute_terminal",
            func=execute_terminal,
            description=(
                "Безопасное выполнение терминальных команд. "
                "Используй для выполнения системных команд (ls, dir, python, и т.д.). "
                "Опасные команды (rm, del, format) запрещены. "
                "Вход: команда (строка)."
            )
        ),
        Tool(
            name="get_weather",
            func=get_weather,
            description=(
                "Получение текущей погоды для указанного города. "
                "Используй когда пользователь спрашивает о погоде. "
                "Вход: название города (строка)."
            )
        ),
        Tool(
            name="get_crypto_price",
            func=get_crypto_price,
            description=(
                "Получение текущего курса криптовалюты. "
                "Используй когда пользователь спрашивает о цене криптовалюты (bitcoin, ethereum и т.д.). "
                "Вход: строка в формате 'coin,currency' или просто 'coin' (валюта по умолчанию usd)."
            )
        ),
        Tool(
            name="generate_qr_code",
            func=generate_qr_code,
            description=(
                "Генерация QR-кода из текста или URL. "
                "Используй когда пользователь просит создать QR-код. "
                "Вход: строка в формате 'данные|путь_к_файлу' или просто 'данные' (файл по умолчанию qr_code.png). "
                "Пример: 'https://example.com|qr.png' или 'Hello World'"
            )
        ),
        Tool(
            name="get_currency_rate",
            func=get_currency_rate,
            description=(
                "Получение курса валют (EUR, USD, RUB и др.). "
                "Используй когда пользователь спрашивает про курс валют. "
                "Вход: пара валют в формате 'USD/EUR' или 'USD to EUR' или 'USD EUR' или просто валюта (тогда базовая USD). "
                "Примеры: 'USD/EUR', 'EUR/RUB', 'USD to RUB', 'EUR' (получит USD/EUR)"
            )
        ),
    ]
    logger.info(f"Создано {len(tools)} инструментов")
    return tools

