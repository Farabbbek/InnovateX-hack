import cv2
import numpy as np
import torch
from ultralytics import YOLO
from pathlib import Path
import time

_original_load = torch.load

def patched_load(*args, **kwargs):
    if 'weights_only' not in kwargs:
        kwargs['weights_only'] = False
    return _original_load(*args, **kwargs)

torch.load = patched_load


class DocumentDetector:
    def __init__(self, model_path, conf_threshold=0.5):
        """
        Инициализация детектора одной моделью
        
        Args:
            model_path: путь к модели
            conf_threshold: порог уверенности
        """
        self.model = YOLO(model_path)
        self.conf_threshold = conf_threshold
        
        model_class_names = self.model.names
        print(f"Model classes: {model_class_names}")

        # Нормализация имён классов модели к каноничным ключам
        def _canonicalize(name: str) -> str:
            s = str(name).strip().lower().replace('-', '_').replace(' ', '_')
            mapping = {
                'qr': 'qr_code',
                'qrcode': 'qr_code',
                'qr_code': 'qr_code',
                'seal': 'stamp',
                'stamp': 'stamp',
                'stamp_seal': 'stamp',
                'signature': 'signature',
                'sign': 'signature',
                'autograph': 'signature',
            }
            return mapping.get(s, s)

        # Создаем маппинг на основе модели и приводим к канону
        if isinstance(model_class_names, dict):
            raw_names = [model_class_names[i] for i in sorted(model_class_names.keys())]
        else:
            raw_names = list(model_class_names)

        self.class_names = [_canonicalize(n) for n in raw_names]
        
        print(f"Model loaded: {model_path}")
        print(f"Classes: {self.class_names}")
    
    def _enhance_image(self, image):
        """Enhances contrast to improve detection."""
        
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # Применяем CLAHE (Contrast Limited Adaptive Histogram Equalization) к L-каналу
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l_enhanced = clahe.apply(l)
        
        # Собираем обратно
        enhanced_lab = cv2.merge([l_enhanced, a, b])
        enhanced_image = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
        
        return enhanced_image
    
    def _create_inverted_image(self, image):
        """Returns inverted image (BGR)."""
        return cv2.bitwise_not(image)
    
    def detect(self, image):
        """Runs detection on original and inverted images and merges results."""
        start_time = time.time()
        
        detections_original = self._detect_on_image(image, "original")
        
        inverted = self._create_inverted_image(image)
        detections_inverted = self._detect_on_image(inverted, "inverted")
        
        all_detections = self._merge_detections(detections_original, detections_inverted)
        
        processing_time = (time.time() - start_time) * 1000
        stats = self._calculate_stats(all_detections)
        
        return {
            'success': True,
            'detections': all_detections,
            'count': len(all_detections),
            'count_by_class': {
                'signature': stats['signature'],
                'stamp': stats['stamp'],
                'qr_code': stats['qr_code']
            },
            'processing_time_ms': round(processing_time, 2),
            'avg_confidence': stats['avg_confidence']
        }
    
    def _detect_on_image(self, image, source_type="original"):
        """Runs single-model detection on an image."""
        
        processed_image = self._enhance_image(image)
        
        # Запуск детекции
        results = self.model.predict(
            source=processed_image,
            conf=self.conf_threshold,
            verbose=False,
            agnostic_nms=True
        )
        
        detections = []
        result = results[0] if isinstance(results, (list, tuple)) else results
        
        if hasattr(result, 'boxes') and result.boxes is not None and len(result.boxes) > 0:
            boxes = result.boxes.xyxy.cpu().numpy()
            confs = result.boxes.conf.cpu().numpy()
            classes = result.boxes.cls.cpu().numpy()
            
            for box, conf, cls in zip(boxes, confs, classes):
                detections.append({
                    'class': int(cls),
                    'class_name': self.class_names[int(cls)],
                    'bbox': box.tolist(),
                    'confidence': float(conf),
                    'source': source_type
                })
        
        return detections
    
    def _merge_detections(self, detections1, detections2, iou_threshold=0.5):
        """
        Объединяет детекции с двух источников, убирая дубликаты
        Оставляет детекцию с большей уверенностью
        """
        if not detections2:
            return detections1
        if not detections1:
            return detections2
        
        merged = list(detections1)
        
        for det2 in detections2:
            is_duplicate = False
            
            for i, det1 in enumerate(merged):
                # Проверяем IoU (Intersection over Union)
                iou = self._calculate_iou(det1['bbox'], det2['bbox'])
                
                if iou > iou_threshold and det1['class'] == det2['class']:
                    is_duplicate = True
                    # Оставляем детекцию с большей уверенностью
                    if det2['confidence'] > det1['confidence']:
                        merged[i] = det2
                    break
            
            if not is_duplicate:
                merged.append(det2)
        
        return merged
    
    def _calculate_iou(self, box1, box2):
        """
        Вычисляет IoU (Intersection over Union) между двумя боксами
        """
        x1_1, y1_1, x2_1, y2_1 = box1
        x1_2, y1_2, x2_2, y2_2 = box2
        
        # Координаты пересечения
        x1_i = max(x1_1, x1_2)
        y1_i = max(y1_1, y1_2)
        x2_i = min(x2_1, x2_2)
        y2_i = min(y2_1, y2_2)
        
        # Площадь пересечения
        if x2_i < x1_i or y2_i < y1_i:
            intersection = 0
        else:
            intersection = (x2_i - x1_i) * (y2_i - y1_i)
        
        # Площади боксов
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        
        # IoU
        union = area1 + area2 - intersection
        
        if union == 0:
            return 0
        
        return intersection / union
    
    def _calculate_stats(self, detections):
        """Подсчёт статистики"""
        stats = {
            'signature': 0,
            'stamp': 0,
            'qr_code': 0,
            'avg_confidence': 0
        }
        
        if not detections:
            return stats
        
        for det in detections:
            class_name = det['class_name']
            # На случай, если входящее имя неканоничное (доп. защита)
            key = class_name
            if key not in stats:
                tmp = class_name.strip().lower().replace('-', '_').replace(' ', '_')
                if tmp in ('qr', 'qrcode'):
                    key = 'qr_code'
                elif tmp in ('seal', 'stamp_seal'):
                    key = 'stamp'
                elif tmp in ('sign', 'autograph'):
                    key = 'signature'
            if key in stats:
                stats[key] += 1
        
        # Средняя уверенность в процентах
        avg_conf = sum(d['confidence'] for d in detections) / len(detections)
        stats['avg_confidence'] = round(avg_conf * 100, 1)
        
        return stats
    
    def draw_detections(self, image, detections):
        """
        Рисование bounding boxes на изображении
        
        Args:
            image: numpy array
            detections: список детекций
        
        Returns:
            изображение с boxes
        """
        img = image.copy()
        
        colors = {
            0: (0, 0, 255),    # Red
            1: (255, 0, 0),    # Blue
            2: (0, 255, 0)     # Green
        }
        
        for det in detections:
            x1, y1, x2, y2 = map(int, det['bbox'])
            cls = det['class']
            conf = det['confidence']
            class_name = det['class_name']
            
            # Рисуем box
            cv2.rectangle(img, (x1, y1), (x2, y2), colors[cls], 2)
            
            # Текст
            label = f"{class_name} {conf:.2f}"
            (text_w, text_h), _ = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2
            )
            
            # Фон для текста
            cv2.rectangle(
                img, (x1, y1 - text_h - 10), 
                (x1 + text_w, y1), colors[cls], -1
            )
            
            # Текст
            cv2.putText(
                img, label, (x1, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2
            )
        
        return img
