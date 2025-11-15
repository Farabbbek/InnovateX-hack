# 📁 Структура проекта Digital Inspector

```
InnovateX-hack/
│
├── 📂 backend/                         # Backend приложение (Flask API)
│   ├── __init__.py                     # Инициализация пакета
│   ├── app.py                          # ⭐ Flask API сервер (главный файл)
│   ├── train.py                        # 🎓 Скрипт обучения YOLOv8m
│   ├── inference.py                    # 🔍 Тестирование модели
│   ├── requirements.txt                # 📦 Python зависимости
│   └── utils/                          # Утилиты
│       ├── __init__.py
│       ├── download_datasets.py        # Скачивание датасетов
│       └── image_utils.py              # Обработка изображений
│
├── 📂 frontend/                        # Frontend приложение
│   ├── index.html                      # 🌐 Главная страница
│   ├── css/
│   │   └── style.css                   # 🎨 Стили (Armeta AI стиль)
│   └── js/
│       ├── animation.js                # ✨ Анимации фона
│       ├── upload.js                   # 📤 Загрузка и API интеграция
│       └── home.js                     # 💾 Экспорт результатов
│
├── 📂 dataset/                         # Датасет для обучения
│   ├── data.yaml                       # ⚙️ Конфигурация датасета
│   ├── raw/                            # Исходные датасеты
│   │   └── .gitkeep
│   ├── images/                         # Изображения
│   │   ├── train/                      # Обучающая выборка
│   │   ├── val/                        # Валидационная выборка
│   │   └── test/                       # Тестовая выборка
│   └── labels/                         # Метки (YOLO формат)
│       ├── train/
│       ├── val/
│       └── test/
│
├── 📂 runs/                            # Результаты обучения
│   └── detect/
│       └── .gitkeep
│
├── 📂 docs/                            # Документация
│   ├── QUICKSTART.md                   # 🚀 Быстрый старт
│   └── API.md                          # 📡 API документация
│
├── 📂 model/                           # Старые файлы модели
│   └── main.py                         # (можно удалить)
│
├── .gitignore                          # Git ignore файл
└── README.md                           # 📖 Основная документация
```

---

## 📊 Статистика проекта

### Backend Files
- ✅ `app.py` - Flask API с детекцией
- ✅ `train.py` - Обучение YOLOv8m
- ✅ `inference.py` - Тестирование на отдельных файлах
- ✅ `requirements.txt` - Все зависимости
- ✅ `utils/download_datasets.py` - Помощник для датасетов
- ✅ `utils/image_utils.py` - Функции обработки

### Frontend Files
- ✅ `index.html` - Красивый интерфейс
- ✅ `css/style.css` - Armeta AI дизайн
- ✅ `js/upload.js` - Интеграция с backend API
- ✅ `js/home.js` - Экспорт результатов
- ✅ `js/animation.js` - Анимированный фон

### Documentation
- ✅ `README.md` - Полная документация
- ✅ `docs/QUICKSTART.md` - Быстрый старт
- ✅ `docs/API.md` - API референс

### Configuration
- ✅ `dataset/data.yaml` - YOLOv8 конфигурация
- ✅ `.gitignore` - Git настройки

---

## 🎯 Ключевые файлы для работы

### Для запуска проекта:
1. **backend/app.py** - Запуск API сервера
2. **frontend/index.html** - Открыть в браузере

### Для обучения модели:
1. **backend/train.py** - Обучение YOLOv8m
2. **dataset/data.yaml** - Конфигурация датасета

### Для тестирования:
1. **backend/inference.py** - Тест на отдельных файлах

---

## 📝 Следующие шаги

### 1. Подготовка датасета
```bash
python backend/utils/download_datasets.py
```

### 2. Обучение модели
```bash
python backend/train.py
```

### 3. Запуск приложения
```bash
# Terminal 1: Backend
cd backend
python app.py

# Terminal 2: Frontend
cd frontend
python -m http.server 8000
```

---

## ✅ Что готово

- [x] Структура проекта
- [x] Backend Flask API
- [x] Frontend интерфейс
- [x] Скрипты обучения
- [x] Утилиты для датасета
- [x] Полная документация
- [x] API интеграция
- [x] Экспорт результатов

---

## ⏳ Что нужно сделать

- [ ] Скачать и подготовить датасет
- [ ] Обучить модель YOLOv8m
- [ ] Протестировать на реальных документах
- [ ] Создать презентацию
- [ ] Записать видео-демо

---

**Проект готов к хакатону! 🚀**
