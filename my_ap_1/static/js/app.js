// Canvas yomg'ir effekti (background)
const canvas = document.createElement('canvas');
canvas.id = 'rainCanvas';
document.body.appendChild(canvas);
const ctx = canvas.getContext('2d');
canvas.width = window.innerWidth;
canvas.height = window.innerHeight;

// Yomg'ir zarralari
let drops = [];
for (let i = 0; i < 150; i++) {
    drops.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        length: 10 + Math.random() * 20,
        speed: 2 + Math.random() * 4
    });
}

function drawRain() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.strokeStyle = 'rgba(255,255,255,0.7)';
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    for (let drop of drops) {
        ctx.moveTo(drop.x, drop.y);
        ctx.lineTo(drop.x, drop.y + drop.length);
        drop.y += drop.speed;
        if (drop.y > canvas.height) drop.y = -drop.length;
    }
    ctx.stroke();
    requestAnimationFrame(drawRain);
}
drawRain();

window.addEventListener('resize', () => {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
});

// Modal funksiyalari
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('hidden');
        modal.classList.add('flex');
    }
}
function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('flex');
        modal.classList.add('hidden');
    }
}

// Smooth scroll
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e){
        e.preventDefault();
        document.querySelector(this.getAttribute('href')).scrollIntoView({
            behavior: 'smooth'
        });
    });
});
