from __future__ import annotations

import base64
import io
import json
import os
from typing import Optional

import cv2
import numpy as np
from PIL import Image

try:
    from pdf2image import convert_from_bytes
    _PDF2IMAGE_AVAILABLE = True
except Exception:
    _PDF2IMAGE_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    _PYMUPDF_AVAILABLE = True
except Exception:
    _PYMUPDF_AVAILABLE = False

# OCR (EasyOCR – без системной установки)
try:
    import easyocr
    _EASYOCR_AVAILABLE = True
except Exception:
    _EASYOCR_AVAILABLE = False

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except Exception:
    pass


def allowed_file(filename: str, allowed_extensions: set[str]) -> bool:
    """Return True if filename has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


def _pil_bytes_to_cv2(img_bytes: bytes) -> np.ndarray:
    """Decode bytes with Pillow and convert to OpenCV BGR array."""
    pil_img = Image.open(io.BytesIO(img_bytes))
    pil_rgb = pil_img.convert('RGB')
    np_img = np.array(pil_rgb)
    return cv2.cvtColor(np_img, cv2.COLOR_RGB2BGR)


def _decode_pdf(raw_bytes: bytes) -> list[np.ndarray]:
    """Convert all pages of a PDF document into image arrays.
    
    Returns:
        List of numpy arrays (one per page)
    """
    attempts: list[str] = []

    if _PDF2IMAGE_AVAILABLE:
        try:
            pages = convert_from_bytes(raw_bytes, dpi=200)
            if pages:
                images = []
                for page in pages:
                    buf = io.BytesIO()
                    page.save(buf, format='JPEG', quality=95)
                    images.append(_pil_bytes_to_cv2(buf.getvalue()))
                return images
            attempts.append('pdf2image returned no pages')
        except Exception as err:
            attempts.append(f'pdf2image: {err}')

    if _PYMUPDF_AVAILABLE:
        try:
            with fitz.open(stream=raw_bytes, filetype='pdf') as pdf_doc:
                if pdf_doc.page_count == 0:
                    attempts.append('PyMuPDF: empty document')
                else:
                    images = []
                    for page_num in range(pdf_doc.page_count):
                        page = pdf_doc.load_page(page_num)
                        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                        images.append(_pil_bytes_to_cv2(pix.tobytes('png')))
                    return images
        except Exception as err:
            attempts.append(f'PyMuPDF: {err}')

    details = '; '.join(attempts) if attempts else 'no PDF backends available'
    raise ValueError(
        'Cannot convert PDF to image. Install pdf2image + Poppler or PyMuPDF. '
        f'Details: {details}'
    )


def load_image_from_upload(file, filename: Optional[str] = None):
    """Read upload stream into OpenCV image(s).
    
    Returns:
        For PDF: list of numpy arrays (one per page)
        For images: single numpy array
    """
    raw_bytes = file.read()

    ext = ''
    if filename and '.' in filename:
        ext = filename.rsplit('.', 1)[1].lower()

    if ext == 'pdf':
        return _decode_pdf(raw_bytes)  # Returns list

    np_bytes = np.frombuffer(raw_bytes, np.uint8)
    img = cv2.imdecode(np_bytes, cv2.IMREAD_COLOR)
    if img is not None:
        return img

    try:
        return _pil_bytes_to_cv2(raw_bytes)
    except Exception as err:
        raise ValueError(
            'Cannot decode file as image. Supported formats: '
            'JPG, JPEG, PNG, BMP, WEBP, TIF/TIFF, HEIC/HEIF, PDF. '
            f'Error: {err}'
        ) from err


def extract_text_from_pdf_bytes(raw_bytes: bytes) -> str:
    """Извлекает текст из PDF используя PyMuPDF, если доступен.

    Возвращает объединённый текст со всех страниц.
    """
    if not _PYMUPDF_AVAILABLE:
        return ''
    try:
        text_parts: list[str] = []
        with fitz.open(stream=raw_bytes, filetype='pdf') as pdf_doc:
            for page_num in range(pdf_doc.page_count):
                page = pdf_doc.load_page(page_num)
                txt = page.get_text('text') or ''
                text_parts.append(txt.strip())
        return '\n'.join(tp for tp in text_parts if tp)
    except Exception:
        return ''


def _enhance_for_ocr(bgr: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    # CLAHE
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    eq = clahe.apply(gray)
    # легкое двоичное + медиана для шумов
    thr = cv2.threshold(eq, 0, 255, cv2.THRESH_OTSU | cv2.THRESH_BINARY)[1]
    thr = cv2.medianBlur(thr, 3)
    return cv2.cvtColor(thr, cv2.COLOR_GRAY2RGB)


def ocr_text_from_images(images: list[np.ndarray], languages: Optional[list[str]] = None, enhance: bool = True) -> str:
    """OCR по списку изображений с помощью EasyOCR (с опциональным препроцессингом)."""
    if not images:
        return ''
    if not _EASYOCR_AVAILABLE:
        return ''
    langs = languages or ['ru', 'en']
    try:
        reader = easyocr.Reader(langs, gpu=False)
        texts: list[str] = []
        for img in images:
            rgb = _enhance_for_ocr(img) if enhance else cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            # Пробуем прямой и инвертированный вариант для тёмного текста
            results = reader.readtext(rgb, detail=0, paragraph=True) or []
            inv = cv2.bitwise_not(rgb)
            results_inv = reader.readtext(inv, detail=0, paragraph=True) or []
            merged = []
            merged.extend([r for r in results if r])
            merged.extend([r for r in results_inv if r])
            if merged:
                texts.append('\n'.join([r for r in merged if isinstance(r, str)]))
        return '\n'.join(t for t in texts if t)
    except Exception:
        return ''


def extract_crops_np(image: np.ndarray, detections: list, padding: int = 20) -> list[np.ndarray]:
    """Возвращает список numpy-кропов по детекциям с паддингом (без base64)."""
    crops = []
    if image is None or not isinstance(image, np.ndarray):
        return crops
    h, w = image.shape[:2]
    for det in detections or []:
        if 'bbox' not in det:
            continue
        x1, y1, x2, y2 = map(int, det['bbox'])
        x1 = max(0, x1 - padding)
        y1 = max(0, y1 - padding)
        x2 = min(w, x2 + padding)
        y2 = min(h, y2 + padding)
        if x2 > x1 and y2 > y1:
            crops.append(image[y1:y2, x1:x2].copy())
    return crops


def guess_document_type(text: str) -> tuple[str, str]:
    """Грубое определение типа документа по ключевым словам. Возвращает (тип, обоснование)."""
    t = (text or '').lower()
    keywords = [
        ('договор', 'Договор: встречается слово "договор".'),
        ('акт', 'Акт: найдено слово "акт" (часто акт приёма-передачи/выполненных работ).'),
        ('накладн', 'Накладная: найдены ключи "накладн".'),
        ('счет-фактура', 'Счёт-фактура: найдено упоминание.'),
        ('счет', 'Счёт: встречается слово "счёт".'),
        ('приказ', 'Приказ: найдено слово "приказ".'),
        ('заявлен', 'Заявление: найдено слово "заявлен".'),
        ('протокол', 'Протокол: найдено слово "протокол".'),
        ('справк', 'Справка: найдены ключи "справк".'),
        ('доверенность', 'Доверенность: найдено слово "доверенность".')
    ]
    for key, reason in keywords:
        if key in t:
            name = reason.split(':', 1)[0]
            return name, reason
    return 'Не определён', 'Ключевые слова типа документа не найдены.'


def build_fallback_summary(counts: dict, doc_type: str, doc_reason: str) -> str:
    sig = counts.get('signature', 0)
    stp = counts.get('stamp', 0)
    qr = counts.get('qr_code', 0)
    parts = []
    parts.append(f"Тип документа: {doc_type} ({doc_reason}).")
    parts.append(f"Найдено: подписи — {sig}, печати — {stp}, QR — {qr}.")
    intent = "вероятно подтверждается содержание документа и согласие сторон"
    if stp > 0 and sig == 0:
        intent = "вероятно документ заверен печатью"
    elif sig > 0 and stp == 0:
        intent = "вероятно подтверждается подписью уполномоченного лица"
    parts.append(f"Итог: документ {('скорее всего ' if (sig>0 or stp>0) else '')}{intent}. Точные детали не обнаружены без текста.")
    return ' '.join(parts)


def simple_summarize(text: str, max_sentences: int = 3) -> str:
    """Простая экстрактивная суммаризация через TF-IDF из scikit-learn.

    Разбиваем на предложения, считаем TF-IDF, выбираем топ-N предложений по суммарному весу.
    """
    import re
    from sklearn.feature_extraction.text import TfidfVectorizer
    import numpy as np

    if not text:
        return ''

    # Сплит предложений (очень простой)
    sents = [s.strip() for s in re.split(r'[\.!?\n]+', text) if s.strip()]
    if not sents:
        return ''
    if len(sents) <= max_sentences:
        return ' '.join(sents)

    try:
        vectorizer = TfidfVectorizer(max_features=10000, stop_words=None)
        X = vectorizer.fit_transform(sents)
        # Сумма TF-IDF по словам в предложении
        scores = X.toarray().sum(axis=1)
        top_idx = np.argsort(scores)[::-1][:max_sentences]
        # Сохраняем порядок как в исходном тексте
        top_idx_sorted = sorted(top_idx)
        summary = ' '.join([sents[i] for i in top_idx_sorted])
        return summary
    except Exception:
        # fallback: первые N предложений
        return ' '.join(sents[:max_sentences])


def image_to_base64(image: np.ndarray) -> str:
    """Encode numpy image as base64 JPEG data URI."""
    success, buffer = cv2.imencode('.jpg', image)
    if not success:
        raise ValueError('Unable to encode image as JPEG')
    img_base64 = base64.b64encode(buffer).decode('utf-8')
    return f'data:image/jpeg;base64,{img_base64}'


def save_detection_result(image: np.ndarray, detections: dict, output_dir: str, filename: str) -> tuple[str, str]:
    """Persist annotated image and detection metadata."""
    image_path = os.path.join(output_dir, 'images', filename)
    cv2.imwrite(image_path, image)

    json_name = filename.rsplit('.', 1)[0] + '.json'
    json_path = os.path.join(output_dir, 'json', json_name)
    with open(json_path, 'w', encoding='utf-8') as handle:
        json.dump(detections, handle, ensure_ascii=False, indent=2)

    return image_path, json_path


def save_detection_result_pdf(images: list[np.ndarray] | np.ndarray, detections: dict, output_dir: str, filename: str) -> tuple[str, str]:
    """Сохраняет аннотированные изображения в один PDF и JSON метаданные.

    images: один np.ndarray (BGR) или список изображений (BGR)
    filename: имя файла с расширением .pdf
    """
    # Нормализуем к списку PIL-изображений в RGB
    if isinstance(images, np.ndarray):
        images_list = [images]
    else:
        images_list = list(images)

    pil_list = []
    for img in images_list:
        if img is None:
            continue
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        pil_list.append(Image.fromarray(rgb))

    if not pil_list:
        raise ValueError('No images to save into PDF')

    # Пути
    pdf_path = os.path.join(output_dir, 'images', filename)
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

    first = pil_list[0]
    rest = pil_list[1:] if len(pil_list) > 1 else []
    # Сохраняем многостраничный PDF
    first.save(pdf_path, format='PDF', resolution=100.0, save_all=bool(rest), append_images=rest)

    # JSON рядом, как и раньше
    json_name = filename.rsplit('.', 1)[0] + '.json'
    json_path = os.path.join(output_dir, 'json', json_name)
    with open(json_path, 'w', encoding='utf-8') as handle:
        json.dump(detections, handle, ensure_ascii=False, indent=2)

    return pdf_path, json_path


def create_response(success: bool, data: Optional[dict] = None, error: Optional[str] = None, status_code: int = 200):
    """Build a uniform response payload for the API."""
    payload = {'success': success}
    if data:
        payload.update(data)
    if error:
        payload['error'] = error
    return payload, status_code


def extract_detection_crops(image: np.ndarray, detections: list, padding: int = 10) -> list[dict]:
    """
    Вырезает области детекций из изображения и возвращает в base64
    
    Args:
        image: numpy array изображения (BGR)
        detections: список детекций с bbox и метаданными
        padding: отступ вокруг bbox в пикселях
    
    Returns:
        список словарей с вырезанными изображениями
    """
    crops = []
    
    for idx, det in enumerate(detections):
        x1, y1, x2, y2 = map(int, det['bbox'])
        
        # Добавляем padding с учетом границ изображения
        crop_x1 = max(0, x1 - padding)
        crop_y1 = max(0, y1 - padding)
        crop_x2 = min(image.shape[1], x2 + padding)
        crop_y2 = min(image.shape[0], y2 + padding)
        
        # Вырезаем область
        crop_img = image[crop_y1:crop_y2, crop_x1:crop_x2]
        
        # Конвертируем в base64
        crop_base64 = image_to_base64(crop_img)
        
        crop_data = {
            'id': f'annotation_{idx + 1}',
            'class': det['class_name'],
            'confidence': round(det['confidence'] * 100, 1),
            'bbox': {
                'x1': float(x1),
                'y1': float(y1),
                'x2': float(x2),
                'y2': float(y2),
                'width': float(x2 - x1),
                'height': float(y2 - y1)
            },
            'crop_bbox': {
                'x1': crop_x1,
                'y1': crop_y1,
                'x2': crop_x2,
                'y2': crop_y2
            },
            'image': crop_base64,
            'size': {
                'width': crop_img.shape[1],
                'height': crop_img.shape[0]
            }
        }
        
        # Добавляем номер страницы если есть
        if 'page' in det:
            crop_data['page'] = det['page']
        
        crops.append(crop_data)
    
    return crops
