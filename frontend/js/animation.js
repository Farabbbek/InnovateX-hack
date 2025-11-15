// Инициализация анимированных частиц на фоне
function initParticles() {
    const bg = document.getElementById('particlesBg');
    const particleCount = 30;
    
    for (let i = 0; i < particleCount; i++) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        particle.style.left = Math.random() * 100 + '%';
        particle.style.top = Math.random() * 100 + '%';
        particle.style.animationDelay = Math.random() * 2 + 's';
        particle.style.animationDuration = (Math.random() * 4 + 4) + 's';
        bg.appendChild(particle);
    }
}

// Запуск при загрузке страницы
document.addEventListener('DOMContentLoaded', initParticles);
