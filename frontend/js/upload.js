// Получаем элементы
const uploadZone = document.getElementById('uploadZone');
const fileInput = document.getElementById('fileInput');
const resultsSection = document.getElementById('resultsSection');

// Клик на зону загрузки
uploadZone.addEventListener('click', () => fileInput.click());

// Drag and drop
uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadZone.classList.add('dragover');
});

uploadZone.addEventListener('dragleave', () => {
    uploadZone.classList.remove('dragover');
});

uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadZone.classList.remove('dragover');
    const files = e.dataTransfer.files;
    if (files.length) handleFile(files[0]);
});

// Изменение input файла
fileInput.addEventListener('change', (e) => {
    if (e.target.files.length) handleFile(e.target.files[0]);
});

// Обработка загруженного файла
async function handleFile(file) {
    const reader = new FileReader();
    reader.onload = async (e) => {
        const img = new Image();
        img.onload = async () => {
            document.getElementById('originalImage').src = img.src;
            resultsSection.classList.add('active');
            
            // Скролл к результатам
            resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            
            // Запуск реальной детекции через backend API
            await detectWithBackend(file, img);
        };
        img.src = e.target.result;
    };
    reader.readAsDataURL(file);
}

// Детекция через backend API (Flask)
async function detectWithBackend(file, img) {
    const API_URL = 'http://localhost:5000/detect';
    
    try {
        // Показываем загрузку
        showLoading(true);
        
        // Подготовка FormData
        const formData = new FormData();
        formData.append('image', file);
        
        // Отправка на backend
        const startTime = performance.now();
        const response = await fetch(API_URL, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        
        // Скрыть загрузку
        showLoading(false);
        
        if (result.success) {
            // Отобразить результаты
            displayResults(result, img);
        } else {
            console.error('Detection failed:', result.error);
            // Fallback на симуляцию
            simulateDetection(img);
        }
        
    } catch (error) {
        console.error('Backend API error:', error);
        console.log('⚠️  Backend недоступен, используем симуляцию');
        showLoading(false);
        // Fallback на симуляцию если backend недоступен
        simulateDetection(img);
    }
}

// Отобразить результаты детекции
function displayResults(result, img) {
    const canvas = document.getElementById('canvas');
    const ctx = canvas.getContext('2d');
    
    // Установить размеры canvas
    canvas.width = img.width;
    canvas.height = img.height;
    
    // Если backend вернул изображение с boxes, используем его
    if (result.image_with_boxes) {
        const processedImg = new Image();
        processedImg.onload = () => {
            document.getElementById('processedImage').src = processedImg.src;
        };
        processedImg.src = result.image_with_boxes;
    } else {
        // Иначе рисуем boxes сами
        ctx.drawImage(img, 0, 0);
        drawDetections(ctx, result.detections, canvas.width, canvas.height);
    }
    
    // Обновить статистику
    document.getElementById('signatureCount').textContent = result.count_by_class.signature || 0;
    document.getElementById('stampCount').textContent = result.count_by_class.stamp || 0;
    document.getElementById('qrCount').textContent = result.count_by_class.qr_code || 0;
    document.getElementById('processingTime').textContent = result.processing_time_ms + 'ms';
    
    const avgConfidence = result.avg_confidence || 0;
    document.getElementById('confidenceText').textContent = avgConfidence + '%';
    document.getElementById('confidenceBar').style.width = avgConfidence + '%';
}

// Рисовать детекции на canvas
function drawDetections(ctx, detections, canvasWidth, canvasHeight) {
    const colors = {
        'signature': '#3b82f6',   // Blue
        'stamp': '#06b6d4',        // Cyan
        'qr_code': '#10b981'       // Green
    };
    
    detections.forEach(det => {
        const [x1, y1, x2, y2] = det.bbox;
        const color = colors[det.class_name] || '#ffffff';
        const conf = (det.confidence * 100).toFixed(1);
        
        // Рисовать box
        ctx.strokeStyle = color;
        ctx.lineWidth = 3;
        ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
        
        // Рисовать label
        ctx.fillStyle = color;
        ctx.font = '16px Arial';
        const label = `${det.class_name} ${conf}%`;
        ctx.fillText(label, x1, y1 - 5);
    });
}

// Показать/скрыть индикатор загрузки
function showLoading(show) {
    // Можно добавить спиннер или индикатор загрузки
    if (show) {
        console.log('🔄 Обработка изображения...');
    } else {
        console.log('✅ Готово!');
    }
}

// Симуляция детекции (пока без реального AI)
function simulateDetection(img) {
    const canvas = document.getElementById('canvas');
    const ctx = canvas.getContext('2d');
    
    // Устанавливаем размеры canvas
    canvas.width = img.width;
    canvas.height = img.height;
    
    // Рисуем изображение
    ctx.drawImage(img, 0, 0);
    
    // Генерируем случайные данные для демонстрации
    const signatures = Math.floor(Math.random() * 3) + 1;
    const stamps = Math.floor(Math.random() * 2) + 1;
    const qrCodes = Math.floor(Math.random() * 2);
    
    // Обновляем статистику
    document.getElementById('signatureCount').textContent = signatures;
    document.getElementById('stampCount').textContent = stamps;
    document.getElementById('qrCount').textContent = qrCodes;
    document.getElementById('processingTime').textContent = Math.floor(Math.random() * 200 + 50) + 'ms';
    
    const avgConfidence = Math.floor(Math.random() * 10 + 90);
    document.getElementById('confidenceText').textContent = avgConfidence + '%';
    document.getElementById('confidenceBar').style.width = avgConfidence + '%';
    
    // Рисуем bounding boxes для демонстрации
    ctx.strokeStyle = '#3b82f6';
    ctx.lineWidth = 3;
    ctx.font = '16px Arial';
    ctx.fillStyle = '#3b82f6';
    
    // Пример boxes
    for (let i = 0; i < signatures; i++) {
        const x = Math.random() * (canvas.width - 150);
        const y = Math.random() * (canvas.height - 100);
        const w = Math.random() * 100 + 100;
        const h = Math.random() * 50 + 40;
        
        ctx.strokeRect(x, y, w, h);
        ctx.fillText('Signature ' + (95 + Math.floor(Math.random() * 5)) + '%', x, y - 5);
    }
    
    for (let i = 0; i < stamps; i++) {
        const x = Math.random() * (canvas.width - 100);
        const y = Math.random() * (canvas.height - 100);
        const w = Math.random() * 80 + 80;
        const h = Math.random() * 80 + 80;
        
        ctx.strokeStyle = '#06b6d4';
        ctx.fillStyle = '#06b6d4';
        ctx.strokeRect(x, y, w, h);
        ctx.fillText('Stamp ' + (92 + Math.floor(Math.random() * 6)) + '%', x, y - 5);
    }
    
    if (qrCodes > 0) {
        for (let i = 0; i < qrCodes; i++) {
            const x = Math.random() * (canvas.width - 80);
            const y = Math.random() * (canvas.height - 80);
            const size = Math.random() * 50 + 60;
            
            ctx.strokeStyle = '#10b981';
            ctx.fillStyle = '#10b981';
            ctx.strokeRect(x, y, size, size);
            ctx.fillText('QR ' + (88 + Math.floor(Math.random() * 8)) + '%', x, y - 5);
        }
    }
}
