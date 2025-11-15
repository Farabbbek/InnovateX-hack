# API Documentation

## Base URL

```
http://localhost:5000
```

## Endpoints

### 1. Health Check

**GET** `/health`

Проверка статуса API и загруженной модели.

**Response:**
```json
{
  "status": "ok",
  "model": "YOLOv8m",
  "model_path": "runs/detect/train/weights/best.pt",
  "model_loaded": true
}
```

---

### 2. Detect Objects

**POST** `/detect`

Детекция объектов на документе.

**Headers:**
```
Content-Type: multipart/form-data
```

**Parameters:**
- `image` (file, required) — Изображение документа (JPG, PNG)

**Response (Success):**
```json
{
  "success": true,
  "detections": [
    {
      "class": 0,
      "class_name": "signature",
      "bbox": [120, 250, 320, 350],
      "confidence": 0.95
    },
    {
      "class": 1,
      "class_name": "stamp",
      "bbox": [500, 100, 650, 250],
      "confidence": 0.92
    }
  ],
  "count": 2,
  "count_by_class": {
    "signature": 1,
    "stamp": 1,
    "qr_code": 0
  },
  "processing_time_ms": 45,
  "avg_confidence": 93,
  "image_with_boxes": "data:image/png;base64,iVBORw0KGgoAAAANSUh..."
}
```

**Response (Error):**
```json
{
  "success": false,
  "error": "Error message"
}
```

**Status Codes:**
- `200 OK` — Success
- `400 Bad Request` — No image provided
- `500 Internal Server Error` — Processing error

---

## Data Types

### Detection Object

```typescript
{
  class: number,           // 0 = signature, 1 = stamp, 2 = qr_code
  class_name: string,      // "signature", "stamp", "qr_code"
  bbox: [number, number, number, number],  // [x1, y1, x2, y2]
  confidence: number       // 0.0 - 1.0
}
```

### Count By Class

```typescript
{
  signature: number,
  stamp: number,
  qr_code: number
}
```

---

## Examples

### Python

```python
import requests

# Детекция объектов
with open('document.jpg', 'rb') as f:
    response = requests.post(
        'http://localhost:5000/detect',
        files={'image': f}
    )

result = response.json()

if result['success']:
    print(f"Найдено: {result['count']} объектов")
    print(f"Подписей: {result['count_by_class']['signature']}")
    print(f"Печатей: {result['count_by_class']['stamp']}")
    print(f"QR-кодов: {result['count_by_class']['qr_code']}")
    print(f"Время: {result['processing_time_ms']}ms")
```

### JavaScript (Fetch)

```javascript
const formData = new FormData();
formData.append('image', fileInput.files[0]);

const response = await fetch('http://localhost:5000/detect', {
    method: 'POST',
    body: formData
});

const result = await response.json();

if (result.success) {
    console.log('Детекции:', result.detections);
    console.log('Всего:', result.count);
}
```

### cURL

```bash
# Health check
curl http://localhost:5000/health

# Детекция
curl -X POST \
  -F "image=@document.jpg" \
  http://localhost:5000/detect
```

---

## Error Handling

Все ошибки возвращаются в формате:

```json
{
  "success": false,
  "error": "Error description"
}
```

**Типичные ошибки:**

- `No image provided` — файл не передан
- `Invalid image format` — неподдерживаемый формат
- `Model not loaded` — модель не загружена
- `Processing error` — ошибка при обработке

---

## Rate Limiting

В текущей версии нет ограничений по частоте запросов.

---

## CORS

CORS включен для всех источников. В production рекомендуется ограничить.
