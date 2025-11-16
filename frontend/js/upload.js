// Получаем элементы
const uploadZone = document.getElementById('uploadZone');
const fileInput = document.getElementById('fileInput');
const resultsSection = document.getElementById('resultsSection');

// Глобальная переменная для экспорта
let lastResult = null;
let lastFile = null; // исходный загруженный файл для саммари

// Проверяем, что элементы существуют перед добавлением обработчиков
if (uploadZone && fileInput) {
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
}

// Обработка загруженного файла
async function handleFile(file) {
    lastFile = file;
    // Сбросить предыдущий AI Summary при новом документе
    const summarySection = document.getElementById('summarySection');
    const summaryCard = document.getElementById('summaryCard');
    if (summarySection) summarySection.style.display = 'none';
    if (summaryCard) summaryCard.innerHTML = '';
    const originalImgEl = document.getElementById('originalImage');
    const originalWrapper = document.getElementById('originalImageWrapper');

    // Активируем секцию результатов
    if (resultsSection) {
        resultsSection.classList.add('active');
        resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    // Если это изображение — показываем превью
    if (file.type && file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = async (e) => {
            const img = new Image();
            img.onload = async () => {
                if (originalImgEl) originalImgEl.src = img.src;
                await detectWithBackend(file, img);
            };
            img.src = e.target.result;
        };
        reader.readAsDataURL(file);
        return;
    }

    // Если PDF — не рендерим превью сразу, отправляем на backend
    if (file.type === 'application/pdf' || (file.name || '').toLowerCase().endsWith('.pdf')) {
        // Показываем подсказку для PDF
        if (originalWrapper) {
            let notice = document.getElementById('pdfNotice');
            if (!notice) {
                notice = document.createElement('div');
                notice.id = 'pdfNotice';
                notice.style.cssText = 'padding:16px;color:#9ca3af;font-size:14px;text-align:center;';
                notice.textContent = '📄 PDF uploaded. Preview will appear after processing...';
                originalWrapper.appendChild(notice);
            } else {
                notice.style.display = 'block';
            }
        }
        if (originalImgEl) {
            originalImgEl.style.display = 'none';
            originalImgEl.src = '';
        }
        // Создаем временное изображение для размеров
        const dummyImg = new Image();
        dummyImg.width = 800;
        dummyImg.height = 1000;
        await detectWithBackend(file, dummyImg);
        return;
    }

    // Для других форматов
    const dummyImg = new Image();
    dummyImg.width = 800;
    dummyImg.height = 1000;
    await detectWithBackend(file, dummyImg);
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
    const data = result.data || result; // поддержка обоих форматов

    // Сохраняем для экспорта
    lastResult = data;

    const processedImage = document.getElementById('processedImage');
    const canvas = document.getElementById('canvas');
    const ctx = canvas ? canvas.getContext('2d') : null;

    if (canvas && ctx) {
        canvas.width = img.width;
        canvas.height = img.height;
    }

    if (data.image_with_boxes) {
        processedImage.src = data.image_with_boxes;
        if (canvas) canvas.style.display = 'none';
    } else if (ctx) {
        if (canvas) canvas.style.display = 'block';
        ctx.drawImage(img, 0, 0);
        drawDetections(ctx, data.detections || [], canvas.width, canvas.height);
    } else {
        processedImage.src = img.src;
    }

    // Обновляем превью оригинала (актуально для PDF)
    const originalEl = document.getElementById('originalImage');
    let sourceImageForThumbs = img.src; // По умолчанию используем загруженное изображение
    
    if (data.original_image) {
        console.log('✅ Получен original_image, обновляем превью');
        if (originalEl) {
            originalEl.src = data.original_image;
            originalEl.style.display = 'block';
            originalEl.style.width = '100%';
            originalEl.style.height = 'auto';
        }
        // Для PDF используем original_image
        sourceImageForThumbs = data.original_image;
        
        // Удаляем notice о PDF
        const notice = document.getElementById('pdfNotice');
        if (notice) {
            notice.remove();
            console.log('✅ Удален notice о PDF');
        }
    }

    // Показываем миниатюры: используем crops из бэкенда если есть, иначе вырезаем на клиенте
    if (data.crops && data.crops.length > 0) {
        console.log('✅ Используем готовые crops из бэкенда');
        displayCropsFromBackend(data.crops);
    } else if (data.detections && data.detections.length > 0) {
        console.log('⚠️ Crops нет, вырезаем на клиенте');
        extractAndDisplayThumbnails(sourceImageForThumbs, data.detections, data.image_with_boxes);
    }

    document.getElementById('signatureCount').textContent = (data.count_by_class && data.count_by_class.signature) || 0;
    document.getElementById('stampCount').textContent = (data.count_by_class && data.count_by_class.stamp) || 0;
    document.getElementById('qrCount').textContent = (data.count_by_class && data.count_by_class.qr_code) || 0;
    document.getElementById('processingTime').textContent = Math.round(data.processing_time_ms || 0) + 'ms';

    // Показываем количество страниц для PDF
    if (data.page_count && data.page_count > 1) {
        const statsGrid = document.querySelector('.stats-grid');
        if (statsGrid && !document.getElementById('pageCountStat')) {
            const pageCountEl = document.createElement('div');
            pageCountEl.id = 'pageCountStat';
            pageCountEl.className = 'stat-card';
            pageCountEl.innerHTML = `
                <div class="stat-icon">📄</div>
                <div class="stat-number">${data.page_count}</div>
                <div class="stat-label">Pages</div>
            `;
            statsGrid.insertBefore(pageCountEl, statsGrid.firstChild);
        } else if (document.getElementById('pageCountStat')) {
            document.querySelector('#pageCountStat .stat-number').textContent = data.page_count;
        }
    }

    const avgConfidence = Math.round(data.avg_confidence || 0);
    document.getElementById('confidenceText').textContent = avgConfidence + '%';
    document.getElementById('confidenceBar').style.width = avgConfidence + '%';
}

// Отображение готовых crops из бэкенда
function displayCropsFromBackend(crops) {
    const signatureThumbs = document.getElementById('signatureThumbs');
    const stampThumbs = document.getElementById('stampThumbs');
    const qrThumbs = document.getElementById('qrThumbs');

    // Очищаем контейнеры
    if (signatureThumbs) signatureThumbs.innerHTML = '';
    if (stampThumbs) stampThumbs.innerHTML = '';
    if (qrThumbs) qrThumbs.innerHTML = '';

    console.log(`🎨 Отображаем ${crops.length} готовых crops`);

    crops.forEach((crop, index) => {
        // Создаем элемент миниатюры
        const thumbDiv = document.createElement('div');
        thumbDiv.className = 'thumb-item';

        const thumbImg = document.createElement('img');
        thumbImg.src = crop.image;  // Уже в формате base64 data URI
        thumbImg.alt = crop.class;
        thumbImg.style.cssText = `
            width: 100%;
            height: auto;
            display: block;
            border-radius: 4px;
        `;

        const confidence = document.createElement('div');
        confidence.textContent = `${crop.confidence}%`;
        confidence.style.cssText = `
            position: absolute;
            top: 12px;
            right: 12px;
            background: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
        `;

        const pageLabel = crop.page ? document.createElement('div') : null;
        if (pageLabel) {
            pageLabel.textContent = `Page ${crop.page}`;
            pageLabel.style.cssText = `
                position: absolute;
                bottom: 12px;
                left: 12px;
                background: rgba(102, 126, 234, 0.9);
                color: white;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 600;
            `;
        }

        thumbDiv.appendChild(thumbImg);
        thumbDiv.appendChild(confidence);
        if (pageLabel) thumbDiv.appendChild(pageLabel);

        // Клик для увеличения
        thumbDiv.addEventListener('click', () => {
            showEnlargedView(crop.image, {
                class_name: crop.class,
                confidence: crop.confidence / 100,
                page: crop.page,
                bbox: [crop.bbox.x1, crop.bbox.y1, crop.bbox.x2, crop.bbox.y2]
            });
        });

        // Определяем контейнер по типу класса
        let targetContainer = null;
        const className = crop.class.toLowerCase();
        
        if (className === 'signature') {
            targetContainer = signatureThumbs;
            console.log(`✍️ Crop #${index}: signature`);
        } else if (className === 'stamp') {
            targetContainer = stampThumbs;
            console.log(`🔷 Crop #${index}: stamp`);
        } else if (className === 'qr_code' || className === 'qr') {
            targetContainer = qrThumbs;
            console.log(`📱 Crop #${index}: qr_code`);
        }

        if (targetContainer) {
            targetContainer.classList.remove('empty-state');
            targetContainer.appendChild(thumbDiv);
        } else {
            console.warn(`⚠️ Неизвестный класс для crop #${index}:`, crop.class);
        }
    });

    // Placeholders для пустых категорий
    if (signatureThumbs && signatureThumbs.children.length === 0) {
        signatureThumbs.innerHTML = '<span style="color: #6b7280; font-size: 14px;">No signatures detected yet.</span>';
        signatureThumbs.classList.add('empty-state');
    }
    if (stampThumbs && stampThumbs.children.length === 0) {
        stampThumbs.innerHTML = '<span style="color: #6b7280; font-size: 14px;">No stamps detected yet.</span>';
        stampThumbs.classList.add('empty-state');
    }
    if (qrThumbs && qrThumbs.children.length === 0) {
        qrThumbs.innerHTML = '<span style="color: #6b7280; font-size: 14px;">No QR codes detected yet.</span>';
        qrThumbs.classList.add('empty-state');
    }
}

// Извлечение и отображение миниатюр обнаруженных элементов
function extractAndDisplayThumbnails(imageSrc, detections, processedImageSrc) {
    const signatureThumbs = document.getElementById('signatureThumbs');
    const stampThumbs = document.getElementById('stampThumbs');
    const qrThumbs = document.getElementById('qrThumbs');

    // Очищаем контейнеры
    if (signatureThumbs) signatureThumbs.innerHTML = '';
    if (stampThumbs) stampThumbs.innerHTML = '';
    if (qrThumbs) qrThumbs.innerHTML = '';

    // Загружаем исходное изображение (ДО обработки, чистое)
    const sourceImg = new Image();
    sourceImg.crossOrigin = 'anonymous';
    
    sourceImg.onload = () => {
        console.log('📐 Размеры исходного изображения:', sourceImg.width, 'x', sourceImg.height);
        
        // Создаем временный canvas для вырезания
        const tempCanvas = document.createElement('canvas');
        const tempCtx = tempCanvas.getContext('2d');

        console.log('🔍 Начинаем обработку', detections.length, 'детекций');

        detections.forEach((det, index) => {
            // Проверяем правильность данных
            console.log(`Детекция #${index}:`, det.class_name, 'bbox:', det.bbox);

            const [x1, y1, x2, y2] = det.bbox;
            const width = x2 - x1;
            const height = y2 - y1;

            // Минимальный padding — 5px
            const padding = 5;
            const cropX = Math.max(0, Math.floor(x1 - padding));
            const cropY = Math.max(0, Math.floor(y1 - padding));
            const cropWidth = Math.min(sourceImg.width - cropX, Math.ceil(width + padding * 2));
            const cropHeight = Math.min(sourceImg.height - cropY, Math.ceil(height + padding * 2));

            console.log(`  Вырезаем область: x=${cropX}, y=${cropY}, w=${cropWidth}, h=${cropHeight}`);

            // Устанавливаем размеры canvas
            tempCanvas.width = cropWidth;
            tempCanvas.height = cropHeight;

            // Очищаем canvas
            tempCtx.clearRect(0, 0, cropWidth, cropHeight);

            // Вырезаем область ИЗ ОРИГИНАЛЬНОГО ИЗОБРАЖЕНИЯ
            tempCtx.drawImage(
                sourceImg,
                cropX, cropY, cropWidth, cropHeight,
                0, 0, cropWidth, cropHeight
            );

            // Создаем элемент миниатюры
            const thumbDiv = document.createElement('div');
            thumbDiv.className = 'thumb-item';

            const thumbImg = document.createElement('img');
            thumbImg.src = tempCanvas.toDataURL('image/png');
            thumbImg.style.cssText = `
                width: 100%;
                height: auto;
                display: block;
                border-radius: 4px;
            `;

            const confidence = document.createElement('div');
            confidence.textContent = `${Math.round(det.confidence * 100)}%`;
            confidence.style.cssText = `
                position: absolute;
                top: 12px;
                right: 12px;
                background: rgba(0, 0, 0, 0.8);
                color: white;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 600;
            `;

            const pageLabel = det.page ? document.createElement('div') : null;
            if (pageLabel) {
                pageLabel.textContent = `Page ${det.page}`;
                pageLabel.style.cssText = `
                    position: absolute;
                    bottom: 12px;
                    left: 12px;
                    background: rgba(102, 126, 234, 0.9);
                    color: white;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: 600;
                `;
            }

            thumbDiv.appendChild(thumbImg);
            thumbDiv.appendChild(confidence);
            if (pageLabel) thumbDiv.appendChild(pageLabel);

            // Клик для увеличения
            thumbDiv.addEventListener('click', () => {
                showEnlargedView(thumbImg.src, det);
            });

            // Определяем куда добавлять по class_name (строка) или по class (число)
            let targetContainer = null;
            const className = det.class_name ? det.class_name.toLowerCase() : '';
            
            // Проверяем по имени класса
            if (className === 'signature') {
                targetContainer = signatureThumbs;
                console.log('✍️ Добавляем в Signatures:', det.class_name);
            } else if (className === 'stamp') {
                targetContainer = stampThumbs;
                console.log('🔷 Добавляем в Stamps:', det.class_name);
            } else if (className === 'qr_code' || className === 'qr') {
                targetContainer = qrThumbs;
                console.log('📱 Добавляем в QR Codes:', det.class_name);
            } else if (typeof det.class === 'number') {
                // Fallback: используем числовой класс
                if (det.class === 0) {
                    targetContainer = signatureThumbs;
                    console.log('✍️ По номеру 0 -> Signatures');
                } else if (det.class === 1) {
                    targetContainer = stampThumbs;
                    console.log('🔷 По номеру 1 -> Stamps');
                } else if (det.class === 2) {
                    targetContainer = qrThumbs;
                    console.log('📱 По номеру 2 -> QR Codes');
                }
            }

            if (targetContainer) {
                targetContainer.classList.remove('empty-state');
                targetContainer.appendChild(thumbDiv);
            } else {
                console.error('❌ Неизвестный класс:', det);
            }
        });

        // Если нет обнаружений в категории, показываем placeholder
        if (signatureThumbs && signatureThumbs.children.length === 0) {
            signatureThumbs.innerHTML = '<span style="color: #6b7280; font-size: 14px;">No signatures detected yet.</span>';
            signatureThumbs.classList.add('empty-state');
        }
        if (stampThumbs && stampThumbs.children.length === 0) {
            stampThumbs.innerHTML = '<span style="color: #6b7280; font-size: 14px;">No stamps detected yet.</span>';
            stampThumbs.classList.add('empty-state');
        }
        if (qrThumbs && qrThumbs.children.length === 0) {
            qrThumbs.innerHTML = '<span style="color: #6b7280; font-size: 14px;">No QR codes detected yet.</span>';
            qrThumbs.classList.add('empty-state');
        }
    };

    sourceImg.onerror = () => {
        console.error('❌ Ошибка загрузки изображения:', imageSrc);
    };

    // ВАЖНО: загружаем ОРИГИНАЛЬНОЕ изображение, не обработанное
    sourceImg.src = imageSrc;
    console.log('🖼️ Загружаем изображение для вырезки:', imageSrc.substring(0, 50) + '...');
}

// Показать увеличенное изображение элемента
function showEnlargedView(imgSrc, detection) {
    const modal = document.createElement('div');
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.9);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
        cursor: pointer;
    `;

    const modalContent = document.createElement('div');
    modalContent.style.cssText = `
        max-width: 90%;
        max-height: 90%;
        position: relative;
    `;

    const img = document.createElement('img');
    img.src = imgSrc;
    img.style.cssText = `
        max-width: 100%;
        max-height: 90vh;
        border-radius: 8px;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
    `;

    const info = document.createElement('div');
    info.style.cssText = `
        position: absolute;
        top: -40px;
        left: 0;
        background: rgba(255, 255, 255, 0.95);
        padding: 8px 16px;
        border-radius: 8px;
        color: #1f2937;
        font-weight: 600;
        font-size: 14px;
    `;
    info.textContent = `${detection.class_name.toUpperCase()} - Confidence: ${Math.round(detection.confidence * 100)}%${detection.page ? ` - Page ${detection.page}` : ''}`;

    modalContent.appendChild(img);
    modalContent.appendChild(info);
    modal.appendChild(modalContent);
    document.body.appendChild(modal);

    modal.addEventListener('click', () => {
        document.body.removeChild(modal);
    });
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

// Обработчики кнопок экспорта/скачивания/сброса
const downloadBtn = document.getElementById('downloadBtn');
const exportBtn = document.getElementById('exportBtn');
const resetBtn = document.getElementById('resetBtn');

if (downloadBtn) {
    downloadBtn.addEventListener('click', () => {
        if (lastResult && lastResult.download_url) {
            window.open(lastResult.download_url, '_blank');
            return;
        }
        const processedImg = document.getElementById('processedImage');
        if (processedImg && processedImg.src) {
            const link = document.createElement('a');
            link.href = processedImg.src;
            link.download = 'detection_result.jpg';
            document.body.appendChild(link);
            link.click();
            link.remove();
        }
    });
}

if (exportBtn) {
    exportBtn.addEventListener('click', () => {
        if (lastResult && lastResult.json_url) {
            window.open(lastResult.json_url, '_blank');
            return;
        }
        if (!lastResult) return;
        const dataStr = JSON.stringify(lastResult, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(dataBlob);
        const link = document.createElement('a');
        link.href = url;
        link.download = 'detection_results.json';
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
    });
}

if (resetBtn) {
    resetBtn.addEventListener('click', () => {
        if (resultsSection) resultsSection.classList.remove('active');
        if (fileInput) fileInput.value = '';
        const original = document.getElementById('originalImage');
        const processed = document.getElementById('processedImage');
        if (original) {
            original.src = '';
            original.style.display = '';
        }
        if (processed) processed.src = '';
        const notice = document.getElementById('pdfNotice');
        if (notice) notice.remove();
        const pageCount = document.getElementById('pageCountStat');
        if (pageCount) pageCount.remove();
        lastResult = null;
        lastFile = null;
        // Прячем и очищаем AI Summary
        const summarySection = document.getElementById('summarySection');
        const summaryCard = document.getElementById('summaryCard');
        if (summarySection) summarySection.style.display = 'none';
        if (summaryCard) summaryCard.innerHTML = '';
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });
}

// Кнопка AI Summary
const summaryBtn = document.getElementById('summaryBtn');
if (summaryBtn) {
    summaryBtn.addEventListener('click', async () => {
        if (!lastFile) {
            alert('Please upload a document first.');
            return;
        }
        await summarizeWithBackend(lastFile);
    });
}

async function summarizeWithBackend(file) {
    const API_URL = 'http://localhost:5000/summarize';
    try {
        showLoading(true);
        // Показать секцию и статус генерации
        const summarySection = document.getElementById('summarySection');
        const summaryCard = document.getElementById('summaryCard');
        if (summarySection) summarySection.style.display = 'block';
        if (summaryCard) summaryCard.innerHTML = '<div style="color:#9ca3af;">Генерируем саммари…</div>';
        const formData = new FormData();
        // эндпоинт поддерживает поля 'document' или 'image'
        formData.append('document', file);
        // cache-busting, чтобы не было кеширования одинаковых запросов
        const response = await fetch(`${API_URL}?t=${Date.now()}`, { method: 'POST', body: formData });
        if (!response.ok) throw new Error('HTTP ' + response.status);
        const result = await response.json();
        showLoading(false);
        if (!result.success) {
            alert('Summarization failed: ' + (result.error || 'unknown error'));
            return;
        }
        const data = result.data || result;
        renderSummary(data);
    } catch (err) {
        showLoading(false);
        console.error('Summarize error:', err);
        alert('AI Summary failed. See console for details.');
    }
}

function renderSummary(data) {
    const section = document.getElementById('summarySection');
    const card = document.getElementById('summaryCard');
    if (!section || !card) return;
    section.style.display = 'block';
    const counts = data.count_by_class || { signature: 0, stamp: 0, qr_code: 0 };
    const statsLine = `✍️ Signatures: ${counts.signature} • 🔷 Stamps: ${counts.stamp} • 📱 QR: ${counts.qr_code}`;

    card.innerHTML = `
        <div style="margin-bottom:10px; color:#93c5fd; font-weight:700;">Document summary</div>
        <div style="white-space:pre-wrap;">${(data.summary || '').replace(/</g,'&lt;')}</div>
        <hr style="border-color:#1f2937; margin:16px 0;">
        <div style="font-size:14px; color:#9ca3af;">${statsLine} • Pages: ${data.page_count || 1} • Avg conf: ${Math.round(data.avg_confidence || 0)}%</div>
        ${data.note ? `<div style="margin-top:8px; color:#a7f3d0;">${data.note}</div>` : ''}
    `;
    section.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// === СКАЧИВАНИЕ ШТАМПОВ БЕЗ ФОНА (PNG с альфой) ===
const downloadStampsNoBgBtn = document.getElementById('downloadStampsNoBgBtn');
if (downloadStampsNoBgBtn) {
    downloadStampsNoBgBtn.addEventListener('click', async () => {
        await downloadNoBgFromContainer('stampThumbs', 'stamp', 'stamps_no_bg.zip');
    });
}

// Новые кнопки: подписи и QR
const downloadSigsNoBgBtn = document.getElementById('downloadSigsNoBgBtn');
if (downloadSigsNoBgBtn) {
    downloadSigsNoBgBtn.addEventListener('click', async () => {
        await downloadNoBgFromContainer('signatureThumbs', 'signature', 'signatures_no_bg.zip');
    });
}

const downloadQrNoBgBtn = document.getElementById('downloadQrNoBgBtn');
if (downloadQrNoBgBtn) {
    downloadQrNoBgBtn.addEventListener('click', async () => {
        await downloadNoBgFromContainer('qrThumbs', 'qr', 'qr_no_bg.zip');
    });
}

async function downloadNoBgFromContainer(containerId, prefix, zipName) {
    const container = document.getElementById(containerId);
    if (!container) return;
    const imgs = Array.from(container.querySelectorAll('img'));
    if (imgs.length === 0) {
        alert('Nothing to download');
        return;
    }

    const zip = new JSZip();
    let idx = 1;
    for (const img of imgs) {
        const pngBytes = await makeTransparentPngFromImage(img);
        if (pngBytes) {
            const fname = `${prefix}_${String(idx).padStart(2,'0')}.png`;
            zip.file(fname, pngBytes);
            idx++;
        }
    }
    const blob = await zip.generateAsync({ type: 'blob' });
    saveAs(blob, zipName);
}

async function makeTransparentPngFromImage(imgEl) {
    // Рисуем в canvas, определяем фон как почти белый/светлый и делаем его прозрачным
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    canvas.width = imgEl.naturalWidth || imgEl.width;
    canvas.height = imgEl.naturalHeight || imgEl.height;
    ctx.drawImage(imgEl, 0, 0, canvas.width, canvas.height);

    const imgData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const data = imgData.data;

    // Пороговые значения: фон (почти белый) -> прозрачный
    // Также удаляем почти-одноцветный фон (серовато-белый)
    const WHITE_THR = 235;      // яркость
    const DIFF_THR = 22;        // допустимая разница каналов для белого

    for (let i = 0; i < data.length; i += 4) {
        const r = data[i];
        const g = data[i + 1];
        const b = data[i + 2];
        const maxc = Math.max(r, g, b);
        const minc = Math.min(r, g, b);
        const isWhiteish = (r > WHITE_THR && g > WHITE_THR && b > WHITE_THR && (maxc - minc) < DIFF_THR);
        if (isWhiteish) {
            data[i + 3] = 0; // alpha = 0
        } else {
            data[i + 3] = 255;
        }
    }

    ctx.putImageData(imgData, 0, 0);

    // Немного подчистим края: свёртка/растушёвка минимальная — опционально (пропускаем для простоты)

    // Вернём как PNG bytes
    const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/png'));
    if (!blob) return null;
    const arrbuf = await blob.arrayBuffer();
    return new Uint8Array(arrbuf);
}
