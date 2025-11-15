"""
Обучение YOLOv8m модели на датасете
Запуск: python backend/train.py
"""

from ultralytics import YOLO
import os

def train_model():
    """Обучить YOLOv8m на датасете"""
    
    print("=" * 60)
    print("🚀 Начинаем обучение YOLOv8m")
    print("=" * 60)
    
    # Загружаем предобученную модель
    model = YOLO('yolov8m.pt')
    print("✅ Базовая модель YOLOv8m загружена")
    
    # Параметры обучения
    results = model.train(
        data='dataset/data.yaml',     # Путь к конфигурации датасета
        epochs=100,                    # Количество эпох
        imgsz=640,                     # Размер изображения
        batch=16,                      # Batch size (для RTX 3070 8GB)
        device=0,                      # GPU (0) или CPU ('cpu')
        patience=20,                   # Early stopping
        save=True,                     # Сохранять чекпоинты
        project='runs/detect',         # Папка для результатов
        name='train',                  # Имя эксперимента
        exist_ok=True,                 # Перезаписать если существует
        pretrained=True,               # Использовать предобученные веса
        optimizer='auto',              # Оптимизатор
        verbose=True,                  # Подробный вывод
        seed=0,                        # Random seed
        deterministic=True,            # Детерминированное обучение
        workers=8,                     # Количество воркеров для загрузки данных
        rect=False,                    # Rectangular training
        cos_lr=True,                   # Cosine learning rate schedule
        lr0=0.01,                      # Начальная learning rate
        lrf=0.01,                      # Финальная learning rate (lr0 * lrf)
        momentum=0.937,                # SGD momentum
        weight_decay=0.0005,           # Optimizer weight decay
        warmup_epochs=3.0,             # Warmup epochs
        warmup_momentum=0.8,           # Warmup momentum
        box=7.5,                       # Box loss gain
        cls=0.5,                       # Class loss gain
        dfl=1.5,                       # DFL loss gain
        plots=True,                    # Сохранять графики обучения
        save_period=10,                # Сохранять каждые N эпох
    )
    
    print("\n" + "=" * 60)
    print("✅ Обучение завершено!")
    print("=" * 60)
    print(f"📁 Модель сохранена в: runs/detect/train/weights/best.pt")
    print(f"📊 Метрики:")
    print(f"   - mAP50: {results.results_dict.get('metrics/mAP50(B)', 'N/A')}")
    print(f"   - mAP50-95: {results.results_dict.get('metrics/mAP50-95(B)', 'N/A')}")
    
    # Валидация на тестовом датасете
    print("\n🧪 Запускаем валидацию на тестовом датасете...")
    metrics = model.val(data='dataset/data.yaml', split='test')
    
    print("\n📈 Финальные метрики на test set:")
    print(f"   - Precision: {metrics.box.mp:.3f}")
    print(f"   - Recall: {metrics.box.mr:.3f}")
    print(f"   - mAP50: {metrics.box.map50:.3f}")
    print(f"   - mAP50-95: {metrics.box.map:.3f}")
    
    return model


if __name__ == '__main__':
    # Проверяем наличие датасета
    if not os.path.exists('dataset/data.yaml'):
        print("❌ Ошибка: Файл dataset/data.yaml не найден!")
        print("📝 Создайте датасет и data.yaml перед обучением")
        exit(1)
    
    train_model()
