/**
 * 360° Panorama Viewer
 * Современный просмотрщик панорам с поддержкой мобильных устройств
 */

class PanoramaViewer {
    constructor(container, imageUrl, options = {}) {
        this.container = typeof container === 'string' ? document.querySelector(container) : container;
        this.imageUrl = imageUrl;
        this.options = {
            autoRotate: false,
            autoRotateSpeed: 0.5,
            mouseZoom: true,
            touchZoom: true,
            enableKeyboard: true,
            showControls: true,
            showFullscreen: true,
            quality: 'optimized', // 'original', 'optimized', 'preview'
            ...options
        };
        
        this.isInitialized = false;
        this.isLoading = false;
        this.panorama = null;
        this.controls = null;
        
        // Touch/Mouse state
        this.isMouseDown = false;
        this.lastMouseX = 0;
        this.lastMouseY = 0;
        this.yaw = 0;
        this.pitch = 0;
        this.zoom = 1;
        
        // Animation
        this.isAutoRotating = this.options.autoRotate;
        this.animationFrame = null;
        
        this.init();
    }
    
    init() {
        if (!this.container) {
            console.error('PanoramaViewer: контейнер не найден');
            return;
        }
        
        this.createHTML();
        this.bindEvents();
        this.loadPanorama();
    }
    
    createHTML() {
        this.container.innerHTML = `
            <div class="panorama-viewer" style="position: relative; width: 100%; height: 100%; overflow: hidden; background: #000;">
                <!-- Загрузчик -->
                <div class="panorama-loader" style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); color: white; text-align: center; z-index: 10;">
                    <div class="spinner" style="border: 3px solid #f3f3f3; border-top: 3px solid #3498db; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 0 auto 10px;"></div>
                    <div>Загрузка панорамы...</div>
                </div>
                
                <!-- Контейнер для панорамы -->
                <div class="panorama-canvas" style="width: 100%; height: 100%; cursor: grab;">
                    <img class="panorama-image" style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); max-width: none; user-select: none; pointer-events: none;" draggable="false" />
                </div>
                
                <!-- Элементы управления -->
                <div class="panorama-controls" style="position: absolute; bottom: 20px; left: 50%; transform: translateX(-50%); display: flex; gap: 10px; z-index: 20;">
                    <button class="control-btn zoom-in" style="background: rgba(0,0,0,0.7); color: white; border: none; border-radius: 50%; width: 40px; height: 40px; cursor: pointer; font-size: 18px;" title="Увеличить">+</button>
                    <button class="control-btn zoom-out" style="background: rgba(0,0,0,0.7); color: white; border: none; border-radius: 50%; width: 40px; height: 40px; cursor: pointer; font-size: 18px;" title="Уменьшить">−</button>
                    <button class="control-btn auto-rotate" style="background: rgba(0,0,0,0.7); color: white; border: none; border-radius: 50%; width: 40px; height: 40px; cursor: pointer; font-size: 14px;" title="Автоповорот">↻</button>
                    <button class="control-btn fullscreen" style="background: rgba(0,0,0,0.7); color: white; border: none; border-radius: 50%; width: 40px; height: 40px; cursor: pointer; font-size: 14px;" title="Полный экран">⛶</button>
                </div>
                
                <!-- Индикатор качества -->
                <div class="quality-indicator" style="position: absolute; top: 20px; right: 20px; background: rgba(0,0,0,0.7); color: white; padding: 5px 10px; border-radius: 15px; font-size: 12px; z-index: 20;">
                    HD
                </div>
                
                <!-- Помощь -->
                <div class="panorama-help" style="position: absolute; top: 20px; left: 20px; background: rgba(0,0,0,0.7); color: white; padding: 10px; border-radius: 8px; font-size: 12px; max-width: 200px; z-index: 20; opacity: 0.8;">
                    <div style="margin-bottom: 5px;"><strong>Управление:</strong></div>
                    <div>• Мышь/палец - поворот</div>
                    <div>• Колёсико/щипок - масштаб</div>
                    <div>• Стрелки - навигация</div>
                </div>
            </div>
        `;
        
        // Добавляем CSS для анимации спиннера
        if (!document.querySelector('#panorama-spinner-css')) {
            const style = document.createElement('style');
            style.id = 'panorama-spinner-css';
            style.textContent = `
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
                .panorama-viewer .control-btn:hover {
                    background: rgba(0,0,0,0.9) !important;
                    transform: scale(1.1);
                }
                .panorama-canvas.grabbing {
                    cursor: grabbing !important;
                }
            `;
            document.head.appendChild(style);
        }
        
        // Получаем ссылки на элементы
        this.loader = this.container.querySelector('.panorama-loader');
        this.canvas = this.container.querySelector('.panorama-canvas');
        this.image = this.container.querySelector('.panorama-image');
        this.controls = this.container.querySelector('.panorama-controls');
        this.qualityIndicator = this.container.querySelector('.quality-indicator');
        this.help = this.container.querySelector('.panorama-help');
        
        // Скрыть помощь через 5 секунд
        setTimeout(() => {
            if (this.help) {
                this.help.style.opacity = '0';
                this.help.style.transition = 'opacity 0.5s';
            }
        }, 5000);
    }
    
    bindEvents() {
        // Кнопки управления
        const zoomInBtn = this.container.querySelector('.zoom-in');
        const zoomOutBtn = this.container.querySelector('.zoom-out');
        const autoRotateBtn = this.container.querySelector('.auto-rotate');
        const fullscreenBtn = this.container.querySelector('.fullscreen');
        
        zoomInBtn?.addEventListener('click', () => this.zoomIn());
        zoomOutBtn?.addEventListener('click', () => this.zoomOut());
        autoRotateBtn?.addEventListener('click', () => this.toggleAutoRotate());
        fullscreenBtn?.addEventListener('click', () => this.toggleFullscreen());
        
        // Mouse events
        this.canvas.addEventListener('mousedown', this.handleMouseDown.bind(this));
        this.canvas.addEventListener('mousemove', this.handleMouseMove.bind(this));
        this.canvas.addEventListener('mouseup', this.handleMouseUp.bind(this));
        this.canvas.addEventListener('mouseleave', this.handleMouseUp.bind(this));
        this.canvas.addEventListener('wheel', this.handleWheel.bind(this));
        
        // Touch events
        this.canvas.addEventListener('touchstart', this.handleTouchStart.bind(this));
        this.canvas.addEventListener('touchmove', this.handleTouchMove.bind(this));
        this.canvas.addEventListener('touchend', this.handleTouchEnd.bind(this));
        
        // Keyboard events
        if (this.options.enableKeyboard) {
            document.addEventListener('keydown', this.handleKeyDown.bind(this));
        }
        
        // Resize event
        window.addEventListener('resize', this.handleResize.bind(this));
    }
    
    async loadPanorama() {
        if (this.isLoading) return;
        
        this.isLoading = true;
        this.showLoader();
        
        try {
            // Загружаем изображение
            await this.loadImage(this.imageUrl);
            this.hideLoader();
            this.isInitialized = true;
            this.startAnimation();
            
            // Обновляем индикатор качества
            this.updateQualityIndicator();
            
        } catch (error) {
            console.error('Ошибка загрузки панорамы:', error);
            this.showError('Ошибка загрузки панорамы');
        }
        
        this.isLoading = false;
    }
    
    loadImage(url) {
        return new Promise((resolve, reject) => {
            const img = new Image();
            img.onload = () => {
                this.image.src = url;
                this.updateImageTransform();
                resolve();
            };
            img.onerror = reject;
            img.src = url;
        });
    }
    
    showLoader() {
        if (this.loader) {
            this.loader.style.display = 'block';
        }
    }
    
    hideLoader() {
        if (this.loader) {
            this.loader.style.display = 'none';
        }
    }
    
    showError(message) {
        if (this.loader) {
            this.loader.innerHTML = `
                <div style="color: #ff6b6b;">
                    <i class="fas fa-exclamation-triangle" style="font-size: 40px; margin-bottom: 10px;"></i>
                    <div>${message}</div>
                </div>
            `;
        }
    }
    
    // Mouse/Touch handlers
    handleMouseDown(e) {
        this.isMouseDown = true;
        this.lastMouseX = e.clientX;
        this.lastMouseY = e.clientY;
        this.canvas.classList.add('grabbing');
        this.stopAutoRotate();
    }
    
    handleMouseMove(e) {
        if (!this.isMouseDown) return;
        
        const deltaX = e.clientX - this.lastMouseX;
        const deltaY = e.clientY - this.lastMouseY;
        
        this.yaw -= deltaX * 0.5;
        this.pitch += deltaY * 0.3;
        this.pitch = Math.max(-90, Math.min(90, this.pitch));
        
        this.updateImageTransform();
        
        this.lastMouseX = e.clientX;
        this.lastMouseY = e.clientY;
    }
    
    handleMouseUp() {
        this.isMouseDown = false;
        this.canvas.classList.remove('grabbing');
    }
    
    handleWheel(e) {
        e.preventDefault();
        if (!this.options.mouseZoom) return;
        
        const delta = e.deltaY > 0 ? -0.1 : 0.1;
        this.zoom = Math.max(0.5, Math.min(3, this.zoom + delta));
        this.updateImageTransform();
    }
    
    handleTouchStart(e) {
        if (e.touches.length === 1) {
            this.handleMouseDown({
                clientX: e.touches[0].clientX,
                clientY: e.touches[0].clientY
            });
        } else if (e.touches.length === 2) {
            // Pinch zoom start
            this.initialPinchDistance = this.getPinchDistance(e.touches);
            this.initialZoom = this.zoom;
        }
    }
    
    handleTouchMove(e) {
        e.preventDefault();
        
        if (e.touches.length === 1 && this.isMouseDown) {
            this.handleMouseMove({
                clientX: e.touches[0].clientX,
                clientY: e.touches[0].clientY
            });
        } else if (e.touches.length === 2 && this.options.touchZoom) {
            // Pinch zoom
            const currentDistance = this.getPinchDistance(e.touches);
            const scale = currentDistance / this.initialPinchDistance;
            this.zoom = Math.max(0.5, Math.min(3, this.initialZoom * scale));
            this.updateImageTransform();
        }
    }
    
    handleTouchEnd() {
        this.handleMouseUp();
    }
    
    getPinchDistance(touches) {
        const dx = touches[0].clientX - touches[1].clientX;
        const dy = touches[0].clientY - touches[1].clientY;
        return Math.sqrt(dx * dx + dy * dy);
    }
    
    handleKeyDown(e) {
        switch (e.key) {
            case 'ArrowLeft':
                this.yaw += 5;
                this.updateImageTransform();
                this.stopAutoRotate();
                break;
            case 'ArrowRight':
                this.yaw -= 5;
                this.updateImageTransform();
                this.stopAutoRotate();
                break;
            case 'ArrowUp':
                this.pitch = Math.min(90, this.pitch + 5);
                this.updateImageTransform();
                break;
            case 'ArrowDown':
                this.pitch = Math.max(-90, this.pitch - 5);
                this.updateImageTransform();
                break;
            case '+':
            case '=':
                this.zoomIn();
                break;
            case '-':
                this.zoomOut();
                break;
            case ' ':
                e.preventDefault();
                this.toggleAutoRotate();
                break;
        }
    }
    
    handleResize() {
        this.updateImageTransform();
    }
    
    updateImageTransform() {
        if (!this.image) return;
        
        const transform = `
            translate(-50%, -50%) 
            scale(${this.zoom}) 
            rotateY(${this.yaw}deg) 
            rotateX(${this.pitch}deg)
        `;
        
        this.image.style.transform = transform;
    }
    
    zoomIn() {
        this.zoom = Math.min(3, this.zoom + 0.2);
        this.updateImageTransform();
    }
    
    zoomOut() {
        this.zoom = Math.max(0.5, this.zoom - 0.2);
        this.updateImageTransform();
    }
    
    toggleAutoRotate() {
        this.isAutoRotating = !this.isAutoRotating;
        
        const btn = this.container.querySelector('.auto-rotate');
        if (btn) {
            btn.style.backgroundColor = this.isAutoRotating ? 'rgba(52, 152, 219, 0.8)' : 'rgba(0,0,0,0.7)';
        }
        
        if (this.isAutoRotating) {
            this.startAnimation();
        }
    }
    
    stopAutoRotate() {
        this.isAutoRotating = false;
        const btn = this.container.querySelector('.auto-rotate');
        if (btn) {
            btn.style.backgroundColor = 'rgba(0,0,0,0.7)';
        }
    }
    
    startAnimation() {
        const animate = () => {
            if (this.isAutoRotating && !this.isMouseDown) {
                this.yaw -= this.options.autoRotateSpeed;
                this.updateImageTransform();
            }
            
            this.animationFrame = requestAnimationFrame(animate);
        };
        
        if (this.animationFrame) {
            cancelAnimationFrame(this.animationFrame);
        }
        
        animate();
    }
    
    toggleFullscreen() {
        if (!document.fullscreenElement) {
            this.container.requestFullscreen();
        } else {
            document.exitFullscreen();
        }
    }
    
    updateQualityIndicator() {
        if (!this.qualityIndicator) return;
        
        const qualityMap = {
            'original': 'ORIG',
            'optimized': 'HD',
            'preview': 'SD'
        };
        
        this.qualityIndicator.textContent = qualityMap[this.options.quality] || 'HD';
    }
    
    // Публичные методы
    setImage(url, quality = 'optimized') {
        this.imageUrl = url;
        this.options.quality = quality;
        this.loadPanorama();
    }
    
    reset() {
        this.yaw = 0;
        this.pitch = 0;
        this.zoom = 1;
        this.updateImageTransform();
    }
    
    destroy() {
        if (this.animationFrame) {
            cancelAnimationFrame(this.animationFrame);
        }
        
        // Удаляем обработчики событий
        window.removeEventListener('resize', this.handleResize.bind(this));
        
        if (this.container) {
            this.container.innerHTML = '';
        }
    }
}

// Экспорт для использования в других модулях
window.PanoramaViewer = PanoramaViewer; 