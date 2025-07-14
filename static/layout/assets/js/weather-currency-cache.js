/**
 * Файл с функциями для кэширования данных о погоде и курсе валюты
 * Данные кэшируются в localStorage и обновляются каждые 6 часов
 */

// Функции для работы с кэшем погоды и курса валют
// Срок действия кэша - 6 часов (в миллисекундах)
const CACHE_EXPIRATION = 6 * 60 * 60 * 1000;

// Функция для сохранения данных о погоде в localStorage
function saveWeatherToCache(weatherData) {
    const dataToSave = {
        ...weatherData,
        timestamp: Date.now()
    };
    localStorage.setItem('weatherCache', JSON.stringify(dataToSave));
}

// Функция для получения данных о погоде из localStorage
function getWeatherFromCache() {
    const cachedData = localStorage.getItem('weatherCache');
    if (!cachedData) return null;

    try {
        const parsedData = JSON.parse(cachedData);

        // Проверяем срок действия кэша
        if (Date.now() - parsedData.timestamp > CACHE_EXPIRATION) {
            // Кэш устарел, удаляем его
            localStorage.removeItem('weatherCache');
            return null;
        }

        return parsedData;
    } catch (e) {
        console.error('Ошибка при парсинге кэша погоды:', e);
        localStorage.removeItem('weatherCache');
        return null;
    }
}

// Функция для сохранения данных о курсе валют в localStorage
function saveCurrencyToCache(currencyData) {
    const dataToSave = {
        ...currencyData,
        timestamp: Date.now()
    };
    localStorage.setItem('currencyCache', JSON.stringify(dataToSave));
}

// Функция для получения данных о курсе валют из localStorage
function getCurrencyFromCache() {
    const cachedData = localStorage.getItem('currencyCache');
    if (!cachedData) return null;

    try {
        const parsedData = JSON.parse(cachedData);

        // Проверяем срок действия кэша
        if (Date.now() - parsedData.timestamp > CACHE_EXPIRATION) {
            // Кэш устарел, удаляем его
            localStorage.removeItem('currencyCache');
            return null;
        }

        return parsedData;
    } catch (e) {
        console.error('Ошибка при парсинге кэша валюты:', e);
        localStorage.removeItem('currencyCache');
        return null;
    }
}

/**
 * Функция для отображения данных о погоде
 * @param {Object} weatherData - Данные о погоде для отображения
 */
function displayWeatherData(weatherData) {
    if (!weatherData) return;

    const temp = weatherData.temp;
    $('#weather-temp').text(`${temp > 0 ? '+' : ''}${temp}°`);

    if (weatherData.iconHtml) {
        $('#weather-icon-container').html(weatherData.iconHtml);
    }
}

/**
 * Функция для отображения данных о курсе валюты
 * @param {Object} currencyData - Данные о курсе валюты для отображения
 */
function displayCurrencyData(currencyData) {
    if (!currencyData) return;

    $('#currency-rate').text(currencyData.rate);
}

// Функция для получения данных о погоде и обновления UI
function getWeather(callback) {
    // Проверка наличия кэша
    const cachedWeather = getWeatherFromCache();
    if (cachedWeather) {
        if (callback) callback(cachedWeather);
        return;
    }

    // Получение данных о погоде через Visual Crossing Weather API
    const city = "Osh,Kyrgyzstan";
    const apiKey = "JPWU9UY254WNDKUNM9MH9E8AR";

    fetch(`https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/${city}/today?unitGroup=metric&key=${apiKey}&include=current`)
        .then(response => response.json())
        .then(data => {
            if (data && data.currentConditions && data.currentConditions.temp !== undefined) {
                // Округляем температуру до целого числа
                const temp = Math.round(data.currentConditions.temp);

                // Получаем код состояния погоды
                const condition = data.currentConditions.conditions ?
                    data.currentConditions.conditions.toLowerCase() : '';
                const iconCode = data.currentConditions.icon ?
                    data.currentConditions.icon.toLowerCase() : '';

                let iconHtml;
                // Определяем иконку на основе кода погоды
                if (iconCode.includes('rain') || condition.includes('дождь') || condition.includes('осадки')) {
                    iconHtml = `<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#4c94f2" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" class="weather-icon"><line x1="16" y1="13" x2="16" y2="21"></line><line x1="8" y1="13" x2="8" y2="21"></line><line x1="12" y1="15" x2="12" y2="23"></line><path d="M20 16.58A5 5 0 0 0 18 7h-1.26A8 8 0 1 0 4 15.25"></path></svg>`;
                } else if (iconCode.includes('snow') || condition.includes('снег')) {
                    iconHtml = `<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#9cc0fa" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" class="weather-icon"><path d="M20 17.58A5 5 0 0 0 18 8h-1.26A8 8 0 1 0 4 16.25"></path><line x1="8" y1="16" x2="8.01" y2="16"></line><line x1="8" y1="20" x2="8.01" y2="20"></line><line x1="12" y1="18" x2="12.01" y2="18"></line><line x1="12" y1="22" x2="12.01" y2="22"></line><line x1="16" y1="16" x2="16.01" y2="16"></line><line x1="16" y1="20" x2="16.01" y2="20"></line></svg>`;
                } else if (iconCode.includes('thunder') || iconCode.includes('lightning') || condition.includes('гроза')) {
                    iconHtml = `<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#7c8aa0" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" class="weather-icon"><path d="M19 16.9A5 5 0 0 0 18 7h-1.26a8 8 0 1 0-11.62 9"></path><polyline points="13 11 9 17 15 17 11 23"></polyline></svg>`;
                } else if (iconCode.includes('fog') || iconCode.includes('mist') || condition.includes('туман') || condition.includes('дымка')) {
                    iconHtml = `<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#7c8aa0" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" class="weather-icon"><path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"></path></svg>`;
                } else if (iconCode === 'clear-day' || iconCode === 'clear-night' || condition.includes('ясно')) {
                    iconHtml = `<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" class="weather-icon"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>`;
                } else if (iconCode.includes('cloud') || condition.includes('облачно') || condition.includes('пасмурно')) {
                    iconHtml = `<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#7c8aa0" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" class="weather-icon"><path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"></path></svg>`;
                } else {
                    iconHtml = `<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#7c8aa0" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" class="weather-icon"><path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"></path></svg>`;
                }

                // Сохраняем данные в кэш
                const weatherData = {
                    temp: temp,
                    iconHtml: iconHtml,
                    condition: condition
                };
                saveWeatherToCache(weatherData);

                // Вызываем колбэк с данными
                if (callback) callback(weatherData);
            } else {
                showFallbackWeather(callback);
            }
        })
        .catch(error => {
            console.error('Ошибка при получении данных о погоде:', error);
            showFallbackWeather(callback);
        });
}

// Функция для отображения резервных данных о погоде
function showFallbackWeather(callback) {
    const month = new Date().getMonth() + 1;

    let temp;
    if (month >= 12 || month <= 2) {
        temp = -2;
    } else if (month >= 3 && month <= 5) {
        temp = 15;
    } else if (month >= 6 && month <= 8) {
        temp = 28;
    } else {
        temp = 12;
    }

    const iconHtml = `<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#7c8aa0" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" class="weather-icon"><path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"></path></svg>`;

    const fallbackData = {
        temp: temp,
        iconHtml: iconHtml,
        condition: 'cloudy'
    };

    saveWeatherToCache(fallbackData);

    if (callback) callback(fallbackData);
}

// Функция для получения курса валют и обновления UI
function getCurrencyRate(callback) {
    // Проверка наличия кэша
    const cachedCurrency = getCurrencyFromCache();
    if (cachedCurrency) {
        if (callback) callback(cachedCurrency);
        return;
    }

    // Получение данных о курсе валют через API
    fetch("https://data.fx.kg/api/v1/central", {
        headers: {
            "Authorization": "Bearer d2WimsDMvhnYStSsq1VRd7jKLZDSS6DQMbzut6rNa9a33c51"
        }
    })
        .then(response => response.json())
        .then(data => {
            if (data && data.usd) {
                const rate = parseFloat(data.usd).toFixed(1);

                const currencyData = {
                    rate: rate,
                    source: 'fx.kg'
                };
                saveCurrencyToCache(currencyData);

                if (callback) callback(currencyData);
            } else {
                getCurrencyRateAlt(callback);
            }
        })
        .catch(() => {
            getCurrencyRateAlt(callback);
        });
}

// Функция для получения альтернативного курса валют
function getCurrencyRateAlt(callback) {
    // Проверка наличия кэша перед запросом
    const cachedCurrency = getCurrencyFromCache();
    if (cachedCurrency) {
        if (callback) callback(cachedCurrency);
        return;
    }

    // Резервный источник - Google Finance
    const scriptURL = "https://script.google.com/macros/s/AKfycbzuBnGgEZdYMvWPJmyqO0eLP7dMWyU45OyEUEGHhdJ7LWNwx1IU7F8Wl_uLF9YADjVx/exec";
    const fullUrl = `${scriptURL}?from=USD&to=KGS&callback=?`;

    $.getJSON(fullUrl, function (data) {
        if (data && data.rate) {
            const rate = parseFloat(data.rate).toFixed(1);

            const currencyData = {
                rate: rate,
                source: 'google'
            };
            saveCurrencyToCache(currencyData);

            if (callback) callback(currencyData);
        } else {
            showFallbackCurrency(callback);
        }
    }).fail(function () {
        showFallbackCurrency(callback);
    });
}

// Функция для отображения резервных данных о курсе валют
function showFallbackCurrency(callback) {
    const fallbackData = {
        rate: '69.8',
        source: 'fallback'
    };

    saveCurrencyToCache(fallbackData);

    if (callback) callback(fallbackData);
} 