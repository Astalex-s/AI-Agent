"""
Утилита для извлечения пути к QR-коду из ответа агента
"""
import os
import re
import glob
import time
import logging

from bot.config import QR_CODE_TIMEOUT, QR_CODES_DIR

logger = logging.getLogger(__name__)


def extract_qr_file_path(response: str) -> str:
    """
    Извлечение пути к файлу QR-кода из ответа агента
    
    Args:
        response: Ответ агента
        
    Returns:
        Путь к файлу QR-кода или None
    """
    # Ищем паттерны типа "QR-код успешно создан: path/to/file.png"
    # Также ищем файлы в директории temp_qr_codes
    patterns = [
        r'QR-код успешно создан:\s*([^\s\n]+\.(png|jpg|jpeg))',
        r'Файл QR-кода:\s*([^\s\n]+\.(png|jpg|jpeg))',
        r'создан:\s*([^\s\n]+\.(png|jpg|jpeg))',
        r'файл[:\s]+([^\s\n]+\.(png|jpg|jpeg))',
        r'([^\s\n]+qr[^\s\n]*\.(png|jpg|jpeg))',  # Любой файл с "qr" в имени
        rf'({QR_CODES_DIR}/[^\s\n]+\.(png|jpg|jpeg))',  # Файлы в директории QR-кодов
    ]
    
    for pattern in patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            file_path = match.group(1)
            # Убираем возможные лишние символы
            file_path = file_path.strip('.,;:()[]')
            # Проверяем существование файла
            if os.path.exists(file_path):
                logger.debug(f"Найден путь к QR-коду: {file_path}")
                return file_path
            # Пробуем относительный путь
            elif not os.path.isabs(file_path):
                if os.path.exists(file_path):
                    logger.debug(f"Найден относительный путь к QR-коду: {file_path}")
                    return file_path
    
    # Также проверяем, есть ли в ответе упоминание QR-кода и ищем файлы .png в директории QR-кодов
    if 'qr' in response.lower() or 'qr-код' in response.lower() or 'qr code' in response.lower():
        # Ищем недавно созданные PNG файлы в директории QR-кодов
        qr_dir_pattern = os.path.join(QR_CODES_DIR, '*.png')
        png_files = glob.glob(qr_dir_pattern)
        
        # Также проверяем текущую директорию на случай, если файл был создан там
        png_files += glob.glob('*.png')
        
        if png_files:
            # Берем самый новый файл
            latest_file = max(png_files, key=os.path.getmtime)
            # Проверяем, что файл был создан недавно
            if time.time() - os.path.getmtime(latest_file) < QR_CODE_TIMEOUT:
                logger.debug(f"Найден недавно созданный QR-код: {latest_file}")
                return latest_file
        
        # Если не нашли по времени, проверяем стандартное имя файла в директории QR-кодов
        default_qr_path = os.path.join(QR_CODES_DIR, 'qr_code.png')
        if os.path.exists(default_qr_path):
            logger.debug(f"Найден QR-код по стандартному пути: {default_qr_path}")
            return default_qr_path
    
    return None

