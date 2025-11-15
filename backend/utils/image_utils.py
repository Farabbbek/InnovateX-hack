"""
Утилиты для обработки изображений и детекций
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple


def draw_bounding_boxes(image: np.ndarray, detections: List[Dict]) -> np.ndarray:
    """
    Рисует bounding boxes на изображении
    
    Args:
        image: numpy array изображения (RGB)
        detections: список детекций с bbox и классами
    
    Returns:
        изображение с нарисованными boxes
    """
    
    # Цвета для разных классов (RGB)
    COLORS = {
        0: (255, 0, 0),      # Red для signature
        1: (0, 0, 255),      # Blue для stamp
        2: (0, 255, 0)       # Green для QR code
    }
    
    CLASS_NAMES = {
        0: 'Signature',
        1: 'Stamp',
        2: 'QR Code'
    }
    
    img = image.copy()
    
    for det in detections:
        x1, y1, x2, y2 = map(int, det['bbox'])
        cls = det['class']
        conf = det['confidence']
        
        # Получить цвет для класса
        color = COLORS.get(cls, (255, 255, 255))
        
        # Нарисовать прямоугольник
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 3)
        
        # Текст с названием и confidence
        label = f"{CLASS_NAMES.get(cls, 'Unknown')} {conf*100:.1f}%"
        
        # Размер текста
        (text_width, text_height), baseline = cv2.getTextSize(
            label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
        )
        
        # Фон для текста
        cv2.rectangle(
            img,
            (x1, y1 - text_height - 10),
            (x1 + text_width, y1),
            color,
            -1
        )
        
        # Текст
        cv2.putText(
            img,
            label,
            (x1, y1 - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2
        )
    
    return img


def calculate_statistics(detections: List[Dict]) -> Dict:
    """
    Вычисляет статистику детекций
    
    Args:
        detections: список детекций
    
    Returns:
        словарь со статистикой
    """
    
    stats = {
        'total': len(detections),
        'by_class': {
            'signature': 0,
            'stamp': 0,
            'qr_code': 0
        },
        'avg_confidence': 0,
        'confidences': []
    }
    
    if not detections:
        return stats
    
    # Подсчёт по классам
    for det in detections:
        class_name = det.get('class_name', 'unknown')
        if class_name in stats['by_class']:
            stats['by_class'][class_name] += 1
        stats['confidences'].append(det['confidence'])
    
    # Средняя уверенность
    if stats['confidences']:
        stats['avg_confidence'] = np.mean(stats['confidences'])
    
    return stats


def resize_image(image: np.ndarray, max_size: int = 1920) -> np.ndarray:
    """
    Изменяет размер изображения с сохранением пропорций
    
    Args:
        image: входное изображение
        max_size: максимальный размер по большей стороне
    
    Returns:
        изображение с новым размером
    """
    
    h, w = image.shape[:2]
    
    if max(h, w) <= max_size:
        return image
    
    # Вычислить новый размер
    if h > w:
        new_h = max_size
        new_w = int(w * (max_size / h))
    else:
        new_w = max_size
        new_h = int(h * (max_size / w))
    
    # Изменить размер
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    
    return resized


def validate_image(image_path: str) -> Tuple[bool, str]:
    """
    Проверяет корректность изображения
    
    Args:
        image_path: путь к изображению
    
    Returns:
        (valid, error_message)
    """
    
    import os
    
    # Проверка существования
    if not os.path.exists(image_path):
        return False, "Файл не найден"
    
    # Проверка расширения
    valid_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
    ext = os.path.splitext(image_path)[1].lower()
    if ext not in valid_extensions:
        return False, f"Неподдерживаемый формат. Используйте: {', '.join(valid_extensions)}"
    
    # Попытка загрузить изображение
    try:
        img = cv2.imread(image_path)
        if img is None:
            return False, "Не удалось загрузить изображение"
        
        # Проверка размера
        h, w = img.shape[:2]
        if h < 32 or w < 32:
            return False, "Изображение слишком маленькое (минимум 32x32)"
        
        if h > 10000 or w > 10000:
            return False, "Изображение слишком большое (максимум 10000x10000)"
        
    except Exception as e:
        return False, f"Ошибка при загрузке: {str(e)}"
    
    return True, ""
