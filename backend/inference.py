"""
Инференс (тестирование) модели на отдельных изображениях
Запуск: python backend/inference.py --image path/to/image.jpg
"""

from ultralytics import YOLO
import cv2
import argparse
import os

def run_inference(image_path, model_path='runs/detect/train/weights/best.pt'):
    """
    Запустить детекцию на изображении
    
    Args:
        image_path: путь к изображению
        model_path: путь к обученной модели
    """
    
    # Проверка существования файлов
    if not os.path.exists(image_path):
        print(f"❌ Изображение не найдено: {image_path}")
        return
    
    if not os.path.exists(model_path):
        print(f"❌ Модель не найдена: {model_path}")
        print("💡 Запустите сначала обучение: python backend/train.py")
        return
    
    # Загрузить модель
    print(f"📦 Загрузка модели: {model_path}")
    model = YOLO(model_path)
    
    # Запустить детекцию
    print(f"🔍 Детекция на: {image_path}")
    results = model.predict(
        source=image_path,
        conf=0.5,           # Порог уверенности
        iou=0.4,            # IoU для NMS
        save=True,          # Сохранить результат
        project='runs/detect',
        name='inference',
        exist_ok=True
    )
    
    # Вывести результаты
    for result in results:
        boxes = result.boxes
        print(f"\n✅ Найдено объектов: {len(boxes)}")
        
        if len(boxes) > 0:
            print("\nДетали:")
            for i, box in enumerate(boxes):
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                class_name = ['signature', 'stamp', 'qr_code'][cls]
                print(f"  {i+1}. {class_name} - {conf*100:.1f}% confidence")
        
        print(f"\n💾 Результат сохранён в: runs/detect/inference/")
    
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Детекция объектов на документах')
    parser.add_argument('--image', '-i', type=str, required=True,
                        help='Путь к изображению документа')
    parser.add_argument('--model', '-m', type=str, 
                        default='runs/detect/train/weights/best.pt',
                        help='Путь к обученной модели')
    
    args = parser.parse_args()
    
    run_inference(args.image, args.model)
