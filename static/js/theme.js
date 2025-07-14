/**
 * Глобальный файл для управления настройками темы и внешнего вида
 */

// Константы для хранения ключей localStorage
const THEME_SETTINGS = {
    COLOR_SCHEME: 'wazir_color_scheme',
    THEME_MODE: 'wazir_theme_mode',
    COMPACT_MODE: 'wazir_compact_mode',
    ANIMATIONS: 'wazir_animations_enabled'
};

// Функция для сохранения настроек в localStorage
function saveThemeSettings(settings) {
    if (settings.colorScheme) {
        localStorage.setItem(THEME_SETTINGS.COLOR_SCHEME, settings.colorScheme);
    }

    if (settings.themeMode !== undefined) {
        localStorage.setItem(THEME_SETTINGS.THEME_MODE, settings.themeMode);
    }

    if (settings.compactMode !== undefined) {
        localStorage.setItem(THEME_SETTINGS.COMPACT_MODE, settings.compactMode);
    }

    if (settings.animationsEnabled !== undefined) {
        localStorage.setItem(THEME_SETTINGS.ANIMATIONS, settings.animationsEnabled);
    }
}

// Функция для загрузки настроек из localStorage
function loadThemeSettings() {
    return {
        colorScheme: localStorage.getItem(THEME_SETTINGS.COLOR_SCHEME) || 'orange',
        themeMode: localStorage.getItem(THEME_SETTINGS.THEME_MODE) || 'light',
        compactMode: localStorage.getItem(THEME_SETTINGS.COMPACT_MODE) === 'true',
        animationsEnabled: localStorage.getItem(THEME_SETTINGS.ANIMATIONS) !== 'false' // По умолчанию включены
    };
}

// Функция для применения сохраненных настроек темы
function applyThemeSettings() {
    const settings = loadThemeSettings();

    // Применяем цветовую схему
    applyColorScheme(settings.colorScheme);

    // Применяем тему (светлая/темная)
    applyThemeMode(settings.themeMode);

    // Применяем компактный режим
    applyCompactMode(settings.compactMode);

    // Применяем настройки анимаций
    applyAnimationsSettings(settings.animationsEnabled);

    return settings;
}

// Применение цветовой схемы
function applyColorScheme(colorScheme) {
    // Устанавливаем data-атрибут для body
    document.documentElement.setAttribute('data-color-scheme', colorScheme);
    if (document.body) {
        document.body.setAttribute('data-color-scheme', colorScheme);
    }

    // При необходимости можно обновить отображение активной схемы
    const swatches = document.querySelectorAll('.color-swatch');
    if (swatches.length > 0) {
        swatches.forEach(swatch => {
            swatch.classList.remove('active');
            if (swatch.getAttribute('data-color') === colorScheme) {
                swatch.classList.add('active');
            }
        });

        // Обновляем скрытое поле, если оно есть
        const colorInput = document.getElementById('color_scheme');
        if (colorInput) {
            colorInput.value = colorScheme;
        }
    }
}

// Применение темы (светлая/темная)
function applyThemeMode(themeMode) {
    if (themeMode === 'dark') {
        document.documentElement.classList.add('dark-theme');
        if (document.body) {
            document.body.classList.add('dark-theme');
        }
    } else {
        document.documentElement.classList.remove('dark-theme');
        if (document.body) {
            document.body.classList.remove('dark-theme');
        }
    }

    // При необходимости обновляем селект выбора темы
    const themeSelect = document.querySelector('select[name="theme"]');
    if (themeSelect) {
        themeSelect.value = themeMode;
    }
}

// Применение компактного режима
function applyCompactMode(isCompact) {
    if (isCompact) {
        document.documentElement.classList.add('compact-mode');
        if (document.body) {
            document.body.classList.add('compact-mode');
        }
    } else {
        document.documentElement.classList.remove('compact-mode');
        if (document.body) {
            document.body.classList.remove('compact-mode');
        }
    }

    // При необходимости обновляем чекбокс
    const compactInput = document.querySelector('input[name="compact_mode"]');
    if (compactInput) {
        compactInput.checked = isCompact;
    }
}

// Применение настроек анимаций
function applyAnimationsSettings(enabled) {
    if (!enabled) {
        document.documentElement.classList.add('no-animations');
        if (document.body) {
            document.body.classList.add('no-animations');
        }
    } else {
        document.documentElement.classList.remove('no-animations');
        if (document.body) {
            document.body.classList.remove('no-animations');
        }
    }

    // При необходимости обновляем чекбокс
    const animationsInput = document.querySelector('input[name="animations_enabled"]');
    if (animationsInput) {
        animationsInput.checked = enabled;
    }
}

// Инициализация настроек при загрузке страницы
document.addEventListener('DOMContentLoaded', function () {
    // Применяем сохраненные настройки
    applyThemeSettings();

    // Устанавливаем обработчики событий для страницы настроек
    setupSettingsPageHandlers();
});

// Настройка обработчиков событий для страницы настроек
function setupSettingsPageHandlers() {
    // Обработчик выбора цветовой схемы
    const colorSwatches = document.querySelectorAll('.color-swatch');
    colorSwatches.forEach(swatch => {
        swatch.addEventListener('click', function () {
            const colorScheme = this.getAttribute('data-color');
            applyColorScheme(colorScheme);
            saveThemeSettings({ colorScheme });
        });
    });

    // Обработчик изменения темы
    const themeSelect = document.querySelector('select[name="theme"]');
    if (themeSelect) {
        themeSelect.addEventListener('change', function () {
            const themeMode = this.value;
            applyThemeMode(themeMode);
            saveThemeSettings({ themeMode });
        });
    }

    // Обработчик переключения компактного режима
    const compactInput = document.querySelector('input[name="compact_mode"]');
    if (compactInput) {
        compactInput.addEventListener('change', function () {
            const isCompact = this.checked;
            applyCompactMode(isCompact);
            saveThemeSettings({ compactMode: isCompact });
        });
    }

    // Обработчик переключения анимаций
    const animationsInput = document.querySelector('input[name="animations_enabled"]');
    if (animationsInput) {
        animationsInput.addEventListener('change', function () {
            const enabled = this.checked;
            applyAnimationsSettings(enabled);
            saveThemeSettings({ animationsEnabled: enabled });
        });
    }

    // Обработчик сохранения всех настроек через API
    const saveButton = document.getElementById('save-button');
    if (saveButton) {
        const originalClickHandler = saveButton.onclick;
        saveButton.onclick = function (event) {
            // Если был установлен оригинальный обработчик, сохраняем его
            if (typeof originalClickHandler === 'function') {
                originalClickHandler.call(this, event);
            }

            // Дополнительно сохраняем все настройки в localStorage
            const notificationForm = document.getElementById('notification-settings-form');
            const appearanceForm = document.getElementById('appearance-settings-form');

            if (appearanceForm) {
                saveThemeSettings({
                    colorScheme: appearanceForm.elements['color_scheme'].value,
                    themeMode: appearanceForm.elements['theme'].value,
                    compactMode: appearanceForm.elements['compact_mode'].checked,
                    animationsEnabled: appearanceForm.elements['animations_enabled'].checked
                });
            }
        };
    }
} 