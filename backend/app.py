"""
Digital Inspector - Flask Backend API
Обрабатывает документы через YOLOv8m модель
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from ultralytics import YOLO
import cv2
import numpy as np
from PIL import Image
import io
import base64
import time
import os

app = Flask(__name__)
CORS(app)  # Разрешить CORS для фронтенда

# Загрузить модель (после обучения)
MODEL_PATH = 'runs/detect/train/weights/best.pt'
if os.path.exists(MODEL_PATH):
    model = YOLO(MODEL_PATH)
    print(f"✅ Модель загружена: {MODEL_PATH}")
else:
    # Для тестирования используем базовую YOLOv8m
    model = YOLO('yolov8m.pt')
    print("⚠️  Используется базовая YOLOv8m (модель не обучена)")

# Названия классов
CLASS_NAMES = ['signature', 'stamp', 'qr_code']

# Цвета для bounding boxes (BGR формат для OpenCV)
COLORS = {
    0: (0, 0, 255),      # Red для подписи
    1: (255, 0, 0),      # Blue для печати
    2: (0, 255, 0)       # Green для QR кода
}


@app.route('/health', methods=['GET'])
def health():
    """Проверка статуса API"""
    return jsonify({
        'status': 'ok',
        'model': 'YOLOv8m',
        'model_path': MODEL_PATH,
        'model_loaded': os.path.exists(MODEL_PATH)
    })


@app.route('/detect', methods=['POST'])
def detect():
    """
    Детекция объектов на документе
    
    Input: FormData с файлом 'image'
    Output: JSON с детекциями и обработанным изображением
    """
    
    # Проверка наличия файла
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    
    file = request.files['image']
    
    try:
        # Читаем изображение
        image_bytes = file.read()
        image = Image.open(io.BytesIO(image_bytes))
        image_np = np.array(image)
        
        # Засекаем время
        start_time = time.time()
        
        # Запускаем модель
        results = model.predict(image_np, conf=0.5, iou=0.4)
        
        # Вычисляем время обработки
        processing_time = int((time.time() - start_time) * 1000)  # в миллисекундах
        
        # Обрабатываем результаты
        detections = []
        count_by_class = {'signature': 0, 'stamp': 0, 'qr_code': 0}
        confidences = []
        
        for result in results:
            boxes = result.boxes.xyxy.cpu().numpy()
            confs = result.boxes.conf.cpu().numpy()
            classes = result.boxes.cls.cpu().numpy()
            
            for box, conf, cls in zip(boxes, confs, classes):
                cls_int = int(cls)
                class_name = CLASS_NAMES[cls_int] if cls_int < len(CLASS_NAMES) else 'unknown'
                
                detection = {
                    'class': cls_int,
                    'class_name': class_name,
                    'bbox': box.tolist(),  # [x1, y1, x2, y2]
                    'confidence': float(conf)
                }
                detections.append(detection)
                count_by_class[class_name] += 1
                confidences.append(float(conf))
        
        # Средняя уверенность
        avg_confidence = int(np.mean(confidences) * 100) if confidences else 0
        
        # Рисуем bounding boxes на изображении
        img_with_boxes = draw_detections(image_np, detections)
        
        # Конвертируем в base64
        _, buffer = cv2.imencode('.png', cv2.cvtColor(img_with_boxes, cv2.COLOR_RGB2BGR))
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return jsonify({
            'success': True,
            'detections': detections,
            'count': len(detections),
            'count_by_class': count_by_class,
            'processing_time_ms': processing_time,
            'avg_confidence': avg_confidence,
            'image_with_boxes': f'data:image/png;base64,{img_base64}'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def draw_detections(image, detections):
    """
    Рисуем bounding boxes на изображении
    
    Args:
        image: numpy array (RGB)
        detections: список детекций
    
    Returns:
        image с нарисованными boxes
    """
    img = image.copy()
    
    for det in detections:
        x1, y1, x2, y2 = map(int, det['bbox'])
        cls = det['class']
        conf = det['confidence']
        class_name = det['class_name']
        
        # Цвет для класса
        color = COLORS.get(cls, (255, 255, 255))
        
        # Рисуем прямоугольник
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 3)
        
        # Текст с названием класса и уверенностью
        label = f"{class_name} {conf*100:.1f}%"
        
        # Размер текста для фона
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
        
        # Сам текст
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


if __name__ == '__main__':
    print("🚀 Digital Inspector Backend запущен!")
    print("📍 API: http://localhost:5000")
    print("🔍 Endpoints:")
    print("   - GET  /health  → Статус API")
    print("   - POST /detect  → Детекция объектов")
    app.run(debug=True, host='0.0.0.0', port=5000)
