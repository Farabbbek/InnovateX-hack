
import os
import shutil
import random
from pathlib import Path


def organize_dataset(
    source_dir,
    output_dir='dataset',
    train_ratio=0.7,
    val_ratio=0.15,
    test_ratio=0.15
):
  
    
    print("🔄 Начинаем разделение датасета...\n")
    print(f"📁 Исходная папка: {source_dir}\n")
    
 
    if not os.path.exists(source_dir):
        print(f"❌ ОШИБКА: Папка не найдена: {source_dir}")
        return
    
   
    for split in ['train', 'val', 'test']:
        os.makedirs(f'{output_dir}/images/{split}', exist_ok=True)
        os.makedirs(f'{output_dir}/labels/{split}', exist_ok=True)
    
    # Получить все изображения (разные расширения)
    source_path = Path(source_dir)
    
    # Попробовать найти файлы
    image_files = []
    extensions = ['*.jpg', '*.JPG', '*.jpeg', '*.JPEG', '*.png', '*.PNG']
    
    print("🔍 Ищем изображения...")
    for ext in extensions:
        found = list(source_path.glob(ext))
        if found:
            print(f"  Найдено {len(found)} файлов {ext}")
            image_files.extend(found)
    
    # Если не нашли напрямую, попробовать подпапки
    if not image_files:
        print("  ⚠️ Файлы не найдены в корне. Ищем в подпапках...")
        for ext in extensions:
            found = list(source_path.rglob(ext))  # recursive!
            if found:
                print(f"  Найдено {len(found)} файлов {ext} в подпапках")
                image_files.extend(found)
    
    if not image_files:
        print(f"\n❌ ОШИБКА: Изображения не найдены в {source_dir}")
        print("\n📋 Содержимое папки:")
        for item in source_path.iterdir():
            print(f"  - {item.name}")
        return
    
    print(f"\n✅ Всего найдено изображений: {len(image_files)}\n")
    
    # Перемешать
    random.shuffle(image_files)
    
    # Вычислить размеры splits
    total = len(image_files)
    train_count = int(total * train_ratio)
    val_count = int(total * val_ratio)
    
    print(f"📋 Распределение:")
    print(f"  Train: {train_count} ({train_ratio*100:.0f}%)")
    print(f"  Val:   {val_count} ({val_ratio*100:.0f}%)")
    print(f"  Test:  {total - train_count - val_count} ({test_ratio*100:.0f}%)\n")
    
    # Распределить по папкам
    copied_count = {'train': 0, 'val': 0, 'test': 0}
    
    for idx, image_file in enumerate(image_files):
        # Определить split
        if idx < train_count:
            split = 'train'
        elif idx < train_count + val_count:
            split = 'val'
        else:
            split = 'test'
        
        # Копировать jpg
        dst_image = f'{output_dir}/images/{split}/{image_file.name}'
        shutil.copy2(image_file, dst_image)
        
        # Копировать txt разметку
        txt_file = image_file.with_suffix('.txt')
        if txt_file.exists():
            dst_label = f'{output_dir}/labels/{split}/{txt_file.name}'
            shutil.copy2(txt_file, dst_label)
            copied_count[split] += 1
        
        # Прогресс каждые 100 файлов
        if (idx + 1) % 100 == 0:
            print(f"  [{idx + 1}/{total}] Обработано...")
    
    # Итоги
    print(f"\n" + "="*50)
    print("✅ РАЗДЕЛЕНИЕ ЗАВЕРШЕНО!")
    print("="*50)
    
    # Проверка
    for split in ['train', 'val', 'test']:
        img_count = len(list(Path(f'{output_dir}/images/{split}').glob('*')))
        lbl_count = len(list(Path(f'{output_dir}/labels/{split}').glob('*.txt')))
        print(f"\n{split.upper()}:")
        print(f"  Изображений: {img_count}")
        print(f"  Разметок: {lbl_count}")
        if img_count != lbl_count:
            print(f"  ⚠️ ВНИМАНИЕ: Количество не совпадает! Возможно не все фото имеют разметку.")
    
    print(f"\n📁 Датасет готов: {output_dir}/")


if __name__ == '__main__':
    # Используем raw string для Windows путей
    organize_dataset(
        source_dir=r'C:\Users\FARAB\Desktop\final dataset', 
        output_dir='dataset',
        train_ratio=0.7,
        val_ratio=0.15,
        test_ratio=0.15
    )
