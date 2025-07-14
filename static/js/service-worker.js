/**
 * Service Worker для обработки Push-уведомлений
 */

// Версия кеша для обновления сервис-воркера
const CACHE_VERSION = 'v1';
const CACHE_NAME = `wazir-cache-${CACHE_VERSION}`;

// URL, которые мы хотим кешировать
const urlsToCache = [
    '/',
    '/static/css/theme.css',
    '/static/js/theme.js',
    '/static/js/notifications.js'
];

// Событие установки сервис-воркера
self.addEventListener('install', (event) => {
    console.log('[Service Worker] Install');
    // Создаем и наполняем кеш
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                console.log('[Service Worker] Caching app shell');
                return cache.addAll(urlsToCache);
            })
    );
});

// Событие активации сервис-воркера
self.addEventListener('activate', (event) => {
    console.log('[Service Worker] Activate');
    // Очищаем старые версии кеша
    event.waitUntil(
        caches.keys().then((keyList) => {
            return Promise.all(keyList.map((key) => {
                if (key !== CACHE_NAME) {
                    console.log('[Service Worker] Removing old cache', key);
                    return caches.delete(key);
                }
            }));
        })
    );
    return self.clients.claim();
});

// Перехватываем запросы и возвращаем кешированные ресурсы, если они есть
self.addEventListener('fetch', (event) => {
    // Игнорируем запросы к API
    if (event.request.url.includes('/api/')) {
        return;
    }

    event.respondWith(
        caches.match(event.request)
            .then((response) => {
                // В случае совпадения возвращаем ресурс из кеша
                if (response) {
                    return response;
                }

                // Если нет в кеше, делаем запрос к сети
                return fetch(event.request);
            })
    );
});

// Обработка события push для показа уведомлений
self.addEventListener('push', (event) => {
    console.log('[Service Worker] Push Received:', event);

    // Получаем данные, переданные с сервера
    let data = { title: 'Новое уведомление', body: 'Вы получили новое уведомление', icon: '/static/layout/assets/img/logo_non.png' };

    if (event.data) {
        try {
            data = event.data.json();
        } catch (e) {
            data.body = event.data.text();
        }
    }

    // Настраиваем опции уведомления
    const options = {
        body: data.body || 'Детали уведомления отсутствуют',
        icon: data.icon || '/static/layout/assets/img/logo_non.png',
        badge: '/static/layout/assets/img/logo_non.png',
        vibrate: [100, 50, 100],
        data: {
            dateOfArrival: Date.now(),
            url: data.url || '/admin/dashboard'
        },
        actions: [
            {
                action: 'open',
                title: 'Открыть'
            },
            {
                action: 'close',
                title: 'Закрыть'
            }
        ]
    };

    // Показываем уведомление
    event.waitUntil(
        self.registration.showNotification(data.title || 'Wazir Уведомление', options)
    );
});

// Обработка клика по уведомлению
self.addEventListener('notificationclick', (event) => {
    console.log('[Service Worker] Notification click:', event.notification.tag);

    // Закрываем уведомление
    event.notification.close();

    // Определяем URL для открытия
    let url = '/admin/dashboard';
    if (event.notification.data && event.notification.data.url) {
        url = event.notification.data.url;
    }

    // Обрабатываем разные действия
    if (event.action === 'open' || !event.action) {
        // Открываем указанную страницу при нажатии
        event.waitUntil(
            clients.matchAll({ type: 'window' })
                .then((clientList) => {
                    // Проверяем, есть ли открытые окна и фокусируемся на них
                    for (const client of clientList) {
                        if (client.url === url && 'focus' in client) {
                            return client.focus();
                        }
                    }

                    // Если нет открытых окон, открываем новое
                    if (clients.openWindow) {
                        return clients.openWindow(url);
                    }
                })
        );
    }
}); 