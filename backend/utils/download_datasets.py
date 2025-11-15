"""
Скрипт для скачивания и подготовки датасетов
Запуск: python backend/utils/download_datasets.py
"""

import os
import shutil
from pathlib import Path

def download_tobacco800():
    """
    Скачать Tobacco-800 датасет
    Содержит реальные документы с подписями
    """
    print("📥 Tobacco-800 Dataset")
    print("   URL: http://tc11.cvc.uab.es/datasets/Tobacco800_1")
    print("   Скачайте вручную и распакуйте в dataset/raw/tobacco800/")
    print()


def download_roboflow_signatures():
    """
    Скачать Roboflow Signature Detection Dataset
    """
    print("📥 Roboflow Signature Detection")
    print("   URL: https://universe.roboflow.com/signature-detection")
    print("   1. Зарегистрируйтесь на Roboflow")
    print("   2. Скачайте в формате YOLOv8")
    print("   3. Распакуйте в dataset/raw/roboflow_signatures/")
    print()


def download_kaggle_stamps():
    """
    Скачать датасет с печатями с Kaggle
    """
    print("📥 Kaggle Stamps Dataset")
    print("   URL: https://www.kaggle.com/search?q=stamp+detection")
    print("   Найдите подходящий датасет с печатями")
    print("   Скачайте и распакуйте в dataset/raw/stamps/")
    print()


def create_qr_dataset():
    """
    Создать датасет с QR кодами
    """
    print("📥 QR Code Dataset")
    print("   Можно использовать:")
    print("   - Сгенерировать QR коды программно")
    print("   - Скачать с Kaggle/Roboflow")
    print("   - Создать вручную с помощью qrcode библиотеки")
    print()


def setup_dataset_structure():
    """
    Создать структуру папок для датасета
    """
    print("📁 Создание структуры папок...")
    
    base_path = Path('dataset')
    
    # Создать папки
    folders = [
        'raw/tobacco800',
        'raw/roboflow_signatures',
        'raw/stamps',
        'raw/qr_codes',
        'images/train',
        'images/val',
        'images/test',
        'labels/train',
        'labels/val',
        'labels/test'
    ]
    
    for folder in folders:
        folder_path = base_path / folder
        folder_path.mkdir(parents=True, exist_ok=True)
        print(f"   ✅ {folder}")
    
    print("\n✅ Структура создана!")
    print()


def print_instructions():
    """
    Вывести инструкции по подготовке датасета
    """
    print("\n" + "=" * 60)
    print("📋 ИНСТРУКЦИИ ПО ПОДГОТОВКЕ ДАТАСЕТА")
    print("=" * 60)
    print()
    print("ШАГИ:")
    print()
    print("1️⃣  Скачайте датасеты из источников выше")
    print("2️⃣  Распакуйте их в папку dataset/raw/")
    print("3️⃣  Конвертируйте в формат YOLO (если нужно)")
    print("4️⃣  Разделите на train/val/test (70/15/15)")
    print("5️⃣  Переместите изображения в dataset/images/")
    print("6️⃣  Переместите метки в dataset/labels/")
    print()
    print("ФОРМАТ МЕТОК YOLO (txt файл):")
    print("   class_id x_center y_center width height")
    print("   Все координаты нормализованы (0-1)")
    print()
    print("ПРИМЕР:")
    print("   0 0.5 0.5 0.2 0.15  # signature в центре")
    print("   1 0.7 0.3 0.1 0.1   # stamp в правом верхнем углу")
    print()
    print("КЛАССЫ:")
    print("   0 - signature")
    print("   1 - stamp")
    print("   2 - qr_code")
    print()
    print("=" * 60)
    print()
    print("💡 После подготовки датасета запустите обучение:")
    print("   python backend/train.py")
    print()


if __name__ == '__main__':
    print("\n🚀 Digital Inspector - Подготовка датасета\n")
    
    # Создать структуру
    setup_dataset_structure()
    
    # Показать ссылки на датасеты
    download_tobacco800()
    download_roboflow_signatures()
    download_kaggle_stamps()
    create_qr_dataset()
    
    # Инструкции
    print_instructions()
