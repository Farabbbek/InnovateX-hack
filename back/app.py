from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import os
import io
import mimetypes
import random
import cv2
import numpy as np
from datetime import datetime

try:
    # При запуске как пакет: gunicorn back.app:app
    from .detector import DocumentDetector
    from .llm import summarize_with_perplexity
    from .utils import *  # noqa: F401,F403
    from .config import Config
    from . import download_model  # noqa: F401
except ImportError:
    # При прямом запуске файла: python back/app.py
    from detector import DocumentDetector
    from llm import summarize_with_perplexity
    from utils import *  # noqa: F401,F403
    from config import Config
    import download_model  # noqa: F401
from dotenv import load_dotenv

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)

load_dotenv()
Config.init_app()

# Загрузка модели (single-model режим)
detector = DocumentDetector(
    model_path=str(Config.MODEL_PATH),
    conf_threshold=Config.CONFIDENCE_THRESHOLD
)

print("Flask server started")


@app.route('/')
def index():
    """Главная страница"""
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/Task.html')
def task_page():
    """Страница детекции"""
    return send_from_directory(app.static_folder, 'Task.html')


@app.route('/health', methods=['GET'])
def health_check():
    """Проверка работоспособности сервера"""
    return jsonify({
        'status': 'ok',
        'model': 'YOLOv8m',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/summarize', methods=['POST'])
def summarize():
    """Демо-саммари по простому правилу: по количеству детекций или случайный ответ.

    Режим выбирается через `Config.SUMMARIZE_MODE`:
    - 'counts'  — формируем текст на основе количества подписей/печатей/QR
    - 'random'  — возвращаем одну из заранее заготовленных фраз (для демонстрации)
    - 'llm'     — старый режим с OCR/LLM (не рекомендуется для демо)
    """
    if 'document' not in request.files and 'image' not in request.files:
        return create_response(False, error='No document file provided (use form field "document")', status_code=400)

    file = request.files.get('document') or request.files.get('image')
    filename = file.filename or ''
    raw_bytes = file.read()
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

    # Подготовим изображения для детекции (без OCR и без LLM по умолчанию)
    page_count = 1
    try:
        if ext == 'pdf':
            images_for_detect = _decode_pdf(raw_bytes)
            page_count = len(images_for_detect)
        else:
            img = load_image_from_upload(io.BytesIO(raw_bytes), filename)
            images_for_detect = img if isinstance(img, list) else [img]
            page_count = len(images_for_detect)
    except Exception:
        # Фолбэк для демо: если не удалось декодировать файл, не падаем — формируем ответ без детекций
        images_for_detect = []
        page_count = 1

    # Считаем детекции
    counts = {'signature': 0, 'stamp': 0, 'qr_code': 0}
    confidences = []
    for page_img in images_for_detect:
        try:
            res = detector.detect(page_img)
            counts['signature'] += res['count_by_class']['signature']
            counts['stamp'] += res['count_by_class']['stamp']
            counts['qr_code'] += res['count_by_class']['qr_code']
            if res['detections']:
                confidences.extend([d['confidence'] for d in res['detections']])
        except Exception:
            # Если детектор упал на странице, продолжаем (демо-устойчивость)
            pass
    avg_conf = round(sum(confidences)/len(confidences)*100, 1) if confidences else 0

    mode = (Config.SUMMARIZE_MODE or 'counts').lower()
    summary = ''
    note = ''

    if mode == 'random':
        options = [
            "Система работает: всё выглядит корректно.",
            "Авто-обзор выполнен. Признаков проблем не обнаружено.",
            "Демо-режим: анализ завершён успешно.",
            "Обработка завершена. Никаких критичных замечаний."
        ]
        summary = random.choice(options)
    elif mode == 'llm':
        # Сохранён старый путь как резервный — но лучше использовать 'counts' для демо
        full_text = ''
        if ext == 'pdf':
            full_text = extract_text_from_pdf_bytes(raw_bytes)
        else:
            try:
                full_text = ocr_text_from_images(images_for_detect, enhance=True)
            except Exception:
                full_text = ''
        if not summary and Config.PERPLEXITY_API_KEY:
            try:
                summary = summarize_with_perplexity(
                    api_key=Config.PERPLEXITY_API_KEY,
                    text=full_text or '',
                    model=Config.PERPLEXITY_MODEL,
                    counts=counts,
                    language='ru'
                ) or ''
            except Exception:
                summary = ''
        if not summary:
            summary = simple_summarize(full_text or '') or ''
        if not summary:
            doc_type, reason = guess_document_type(full_text or '')
            summary = build_fallback_summary(counts, doc_type, reason)
    else:
        # counts-режим: простая логика на основе количества детекций
        sig = counts['signature']
        stp = counts['stamp']
        qr = counts['qr_code']
        if sig > 0 and stp > 0:
            summary = f"Найдено подписей: {sig} и печатей: {stp}. Документ, вероятно, подписан и заверен. QR: {qr}."
        elif sig > 0:
            summary = f"Обнаружено подписей: {sig}. Документ, вероятно, подписан. QR: {qr}."
        elif stp > 0:
            summary = f"Обнаружено печатей/штампов: {stp}. Документ, вероятно, заверен. QR: {qr}."
        elif qr > 0:
            summary = f"Найдено QR-кодов: {qr}. Подписей и печатей не обнаружено."
        else:
            summary = "Подписей, печатей и QR-кодов не обнаружено."

    data = {
        'summary': summary,
        'text_preview': '',
        'word_count': 0,
        'page_count': page_count,
        'count_by_class': counts,
        'avg_confidence': avg_conf,
        'note': note
    }

    return create_response(True, data=data)


@app.route('/detect', methods=['POST'])
def detect():
    """
    Endpoint для детекции объектов
    
    Ожидает:
        - Файл изображения в FormData с ключом 'image'
    
    Возвращает:
        JSON с результатами детекции
    """
    
    # Проверка наличия файла
    if 'image' not in request.files:
        return create_response(
            success=False,
            error='No image file provided',
            status_code=400
        )
    
    file = request.files['image']
    
    # Проверка имени файла
    if file.filename == '':
        return create_response(
            success=False,
            error='Empty filename',
            status_code=400
        )
    
    # Проверка расширения
    if not allowed_file(file.filename, Config.ALLOWED_EXTENSIONS):
        return create_response(
            success=False,
            error=f'Invalid file type. Allowed: {Config.ALLOWED_EXTENSIONS}',
            status_code=400
        )
    
    try:
        # Загрузка изображения/документа
        image = load_image_from_upload(file, file.filename)
        
        # Проверяем, является ли это PDF (список страниц) или одно изображение
        is_pdf = isinstance(image, list)
        
        if is_pdf:
            # Multi-page PDF processing
            all_detections = []
            all_pages_annotated = []
            total_stats = {'signature': 0, 'stamp': 0, 'qr_code': 0}
            total_time = 0
            confidences = []
            
            for page_num, page_image in enumerate(image, start=1):
                # Детекция на каждой странице
                page_results = detector.detect(page_image)
                
                # Рисование результатов
                page_annotated = detector.draw_detections(page_image, page_results['detections'])
                all_pages_annotated.append(page_annotated)
                
                # Добавляем номер страницы к каждой детекции
                for det in page_results['detections']:
                    det['page'] = page_num
                
                all_detections.extend(page_results['detections'])
                
                # Суммируем статистику
                total_stats['signature'] += page_results['count_by_class']['signature']
                total_stats['stamp'] += page_results['count_by_class']['stamp']
                total_stats['qr_code'] += page_results['count_by_class']['qr_code']
                total_time += page_results['processing_time_ms']
                
                if page_results['detections']:
                    confidences.extend([d['confidence'] for d in page_results['detections']])
            
            # Объединяем все страницы вертикально только для предпросмотра во фронте
            combined_image = np.vstack(all_pages_annotated)
            combined_original = np.vstack(image)
            
            # Извлекаем crops из оригинального изображения
            crops = extract_detection_crops(combined_original, all_detections, padding=10)
            
            # Сохранение результатов в PDF (по страницам)
            filename = f"result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            img_path, json_path = save_detection_result_pdf(
                all_pages_annotated,
                {
                    'detections': all_detections,
                    'crops': crops,
                    'count': len(all_detections),
                    'count_by_class': total_stats,
                    'page_count': len(image),
                    'processing_time_ms': round(total_time, 2)
                },
                Config.OUTPUT_DIR,
                filename
            )
            
            # Формируем ответ
            results = {
                'success': True,
                'detections': all_detections,
                'crops': crops,
                'count': len(all_detections),
                'count_by_class': total_stats,
                'page_count': len(image),
                'processing_time_ms': round(total_time, 2),
                'avg_confidence': round(sum(confidences) / len(confidences) * 100, 1) if confidences else 0,
                'image_with_boxes': image_to_base64(combined_image),
                'original_image': image_to_base64(combined_original),
                'filename': filename
            }
        else:
            # Single image processing
            results = detector.detect(image)
            
            # Рисование результатов
            image_with_boxes = detector.draw_detections(image, results['detections'])
            
            # Извлекаем crops из оригинального изображения
            crops = extract_detection_crops(image, results['detections'], padding=10)
            
            # Сохранение результатов в PDF (1 страница)
            filename = f"result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            img_path, json_path = save_detection_result_pdf(
                [image_with_boxes],
                {**results, 'crops': crops},
                Config.OUTPUT_DIR,
                filename
            )
            
            # Конвертация изображения в base64 для отправки на фронт
            results['image_with_boxes'] = image_to_base64(image_with_boxes)
            results['original_image'] = image_to_base64(image)
            results['crops'] = crops
            results['filename'] = filename

        # Полные URL для скачивания (работает даже если фронт открыт как file://)
        origin = request.host_url.rstrip('/')
        results['download_url'] = f"{origin}/download/{filename}"
        json_filename = os.path.splitext(filename)[0] + '.json'
        results['json_url'] = f"{origin}/download_json/{json_filename}"
        
        return create_response(success=True, data=results)
        
    except Exception as e:
        return create_response(
            success=False,
            error=str(e),
            status_code=500
        )


@app.route('/detect_batch', methods=['POST'])
def detect_batch():
    """
    Endpoint для пакетной детекции (несколько изображений)
    """
    
    if 'images' not in request.files:
        return create_response(
            success=False,
            error='No images provided',
            status_code=400
        )
    
    files = request.files.getlist('images')
    
    results_list = []
    
    for file in files:
        try:
            image = load_image_from_upload(file)
            results = detector.detect(image)
            results['filename'] = file.filename
            results_list.append(results)
        except Exception as e:
            results_list.append({
                'filename': file.filename,
                'success': False,
                'error': str(e)
            })
    
    return create_response(
        success=True,
        data={'results': results_list, 'count': len(results_list)}
    )


@app.route('/download/<filename>', methods=['GET'])
def download_result(filename):
    """Скачивание обработанного изображения"""
    
    file_path = os.path.join(Config.OUTPUT_DIR, 'images', filename)
    
    if not os.path.exists(file_path):
        return create_response(
            success=False,
            error='File not found',
            status_code=404
        )
    
    mime = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
    return send_file(file_path, mimetype=mime, as_attachment=True)


@app.route('/download_json/<filename>', methods=['GET'])
def download_json(filename):
    """Скачивание JSON с результатами"""
    file_path = os.path.join(Config.OUTPUT_DIR, 'json', filename)
    if not os.path.exists(file_path):
        return create_response(
            success=False,
            error='File not found',
            status_code=404
        )
    return send_file(file_path, mimetype='application/json', as_attachment=True)


@app.route('/stats', methods=['GET'])
def get_stats():
    """Получение статистики обработанных файлов"""
    
    images_dir = os.path.join(Config.OUTPUT_DIR, 'images')
    json_dir = os.path.join(Config.OUTPUT_DIR, 'json')
    
    stats = {
        'processed_images': len(os.listdir(images_dir)) if os.path.exists(images_dir) else 0,
        'json_results': len(os.listdir(json_dir)) if os.path.exists(json_dir) else 0,
    }
    
    return create_response(success=True, data=stats)


@app.route('/detect_dataset', methods=['POST'])
def detect_dataset():
    """Детекция с выводом в формате аннотаций (как в примере: file -> page_X -> annotations).

    Формат ответа:
    {
      "<filename>": {
         "page_1": {
            "annotations": [ {"annotation_1": {"category": "signature", "bbox": {...}, "area": ...}}, ...],
            "page_size": {"width": W, "height": H}
         },
         ...
      }
    }
    """
    if 'image' not in request.files and 'document' not in request.files:
        return create_response(False, error='No file provided (use field "image" or "document")', status_code=400)

    file = request.files.get('image') or request.files.get('document')
    filename = file.filename or 'uploaded'

    try:
        loaded = load_image_from_upload(file, filename)
    except Exception as e:
        return create_response(False, error=f'Failed to decode file: {e}', status_code=400)

    is_pdf = isinstance(loaded, list)
    pages = loaded if is_pdf else [loaded]

    # Выполняем детекцию постранично
    annotation_root = {filename: {}}
    total_counts = {'signature': 0, 'stamp': 0, 'qr_code': 0}
    ann_global_index = 1

    for page_idx, page_img in enumerate(pages, start=1):
        try:
            res = detector.detect(page_img)
        except Exception:
            # Если детекция упала — пропускаем страницу, но добавляем размер
            h, w = page_img.shape[:2]
            annotation_root[filename][f'page_{page_idx}'] = {
                'annotations': [],
                'page_size': {'width': w, 'height': h}
            }
            continue

        # Размер страницы
        h, w = page_img.shape[:2]
        page_key = f'page_{page_idx}'
        page_entry = {
            'annotations': [],
            'page_size': {'width': w, 'height': h}
        }

        for det in res['detections']:
            x1, y1, x2, y2 = det['bbox']
            width = x2 - x1
            height = y2 - y1
            area = width * height
            ann_id = f'annotation_{ann_global_index}'
            ann_global_index += 1
            page_entry['annotations'].append({
                ann_id: {
                    'category': det['class_name'],
                    'bbox': {
                        'x': int(x1),
                        'y': int(y1),
                        'width': float(width),
                        'height': float(height)
                    },
                    'area': float(area)
                }
            })

        # Суммируем счётчики
        total_counts['signature'] += res['count_by_class']['signature']
        total_counts['stamp'] += res['count_by_class']['stamp']
        total_counts['qr_code'] += res['count_by_class']['qr_code']

        annotation_root[filename][page_key] = page_entry

    data = {
        'annotations': annotation_root,
        'counts_total': total_counts,
        'page_count': len(pages)
    }

    return create_response(True, data=data)


if __name__ == '__main__':
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG
    )
