// Скачивание результатов
document.getElementById('downloadBtn').addEventListener('click', () => {
    const canvas = document.getElementById('canvas');
    const link = document.createElement('a');
    link.href = canvas.toDataURL();
    link.download = 'detection_results.png';
    link.click();
});

// Экспорт JSON
document.getElementById('exportBtn').addEventListener('click', () => {
    const data = {
        signatures: parseInt(document.getElementById('signatureCount').textContent),
        stamps: parseInt(document.getElementById('stampCount').textContent),
        qr_codes: parseInt(document.getElementById('qrCount').textContent),
        processing_time_ms: parseInt(document.getElementById('processingTime').textContent),
        confidence_score: parseInt(document.getElementById('confidenceText').textContent),
        timestamp: new Date().toISOString()
    };
    
    const link = document.createElement('a');
    link.href = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(data, null, 2));
    link.download = 'detection_results.json';
    link.click();
});

// Сброс
document.getElementById('resetBtn').addEventListener('click', () => {
    const resultsSection = document.getElementById('resultsSection');
    resultsSection.classList.remove('active');
    document.getElementById('fileInput').value = '';
    document.getElementById('originalImage').src = '';
    document.getElementById('processedImage').src = '';
});
