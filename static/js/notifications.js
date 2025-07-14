/**
 * JavaScript-файл для работы с Push-уведомлениями в браузере
 */

// Проверяем поддержку Service Worker и Push API
const pushSupported = 'serviceWorker' in navigator && 'PushManager' in window;

// Ключ для сохранения статуса подписки в localStorage
const PUSH_SUBSCRIPTION_KEY = 'wazir_push_subscription';

// Функция для регистрации Service Worker
async function registerServiceWorker() {
    if (!pushSupported) {
        console.warn('Push уведомления не поддерживаются в этом браузере');
        return null;
    }

    try {
        const registration = await navigator.serviceWorker.register('/static/js/service-worker.js');
        console.log('Service Worker успешно зарегистрирован:', registration);
        return registration;
    } catch (error) {
        console.error('Ошибка при регистрации Service Worker:', error);
        return null;
    }
}

// Функция для запроса разрешения на получение уведомлений
async function requestNotificationPermission() {
    if (!("Notification" in window)) {
        console.warn("Этот браузер не поддерживает уведомления");
        return false;
    }

    try {
        const permission = await Notification.requestPermission();
        return permission === "granted";
    } catch (error) {
        console.error('Ошибка при запросе разрешения на уведомления:', error);
        return false;
    }
}

// Функция для получения текущей подписки или создания новой
async function getOrCreateSubscription(registration) {
    try {
        let subscription = await registration.pushManager.getSubscription();

        if (!subscription) {
            // Получаем VAPID ключ с сервера
            const response = await fetch('/api/v1/push/vapid-key');
            const vapidData = await response.json();

            if (!vapidData.publicKey) {
                throw new Error('Не удалось получить VAPID публичный ключ');
            }

            // Преобразуем строку в Uint8Array для API
            const convertedVapidKey = urlBase64ToUint8Array(vapidData.publicKey);

            // Создаем новую подписку
            subscription = await registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: convertedVapidKey
            });
        }

        return subscription;
    } catch (error) {
        console.error('Ошибка при получении/создании подписки:', error);
        return null;
    }
}

// Сохраняем подписку на сервере
async function saveSubscriptionOnServer(subscription) {
    try {
        const response = await fetch('/api/v1/push/subscribe', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify(subscription)
        });

        const data = await response.json();
        if (data.success) {
            // Сохраняем статус подписки в localStorage для быстрого доступа
            localStorage.setItem(PUSH_SUBSCRIPTION_KEY, 'true');
            return true;
        } else {
            console.error('Ошибка при сохранении подписки:', data.message);
            return false;
        }
    } catch (error) {
        console.error('Ошибка при сохранении подписки на сервере:', error);
        return false;
    }
}

// Отписка от Push-уведомлений
async function unsubscribeFromPush() {
    try {
        const registration = await navigator.serviceWorker.ready;
        const subscription = await registration.pushManager.getSubscription();

        if (!subscription) {
            console.log('Нет активной подписки для отмены');
            localStorage.removeItem(PUSH_SUBSCRIPTION_KEY);
            return true;
        }

        // Отправляем запрос на сервер для удаления подписки
        const response = await fetch('/api/v1/push/unsubscribe', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify(subscription)
        });

        // Отменяем подписку на стороне клиента
        await subscription.unsubscribe();

        // Удаляем запись из localStorage
        localStorage.removeItem(PUSH_SUBSCRIPTION_KEY);

        return true;
    } catch (error) {
        console.error('Ошибка при отписке от Push-уведомлений:', error);
        return false;
    }
}

// Отправка тестового уведомления
async function sendTestPushNotification() {
    try {
        const response = await fetch('/api/v1/push/test', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        });

        const data = await response.json();
        if (data.success) {
            console.log('Тестовое уведомление отправлено');
            return true;
        } else {
            console.error('Ошибка при отправке тестового уведомления:', data.message);
            return false;
        }
    } catch (error) {
        console.error('Ошибка при отправке запроса тестового уведомления:', error);
        return false;
    }
}

// Вспомогательная функция для конвертации base64 в Uint8Array
function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
        .replace(/-/g, '+')
        .replace(/_/g, '/');

    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
}

// Работа с интерфейсом для включения/отключения push-уведомлений
async function setupPushNotifications(enabled) {
    try {
        if (enabled) {
            // Запрашиваем разрешение на уведомления
            const permissionGranted = await requestNotificationPermission();
            if (!permissionGranted) {
                console.warn('Разрешение на уведомления не получено');
                return false;
            }

            // Регистрируем сервис-воркер
            const registration = await registerServiceWorker();
            if (!registration) {
                return false;
            }

            // Получаем или создаем подписку
            const subscription = await getOrCreateSubscription(registration);
            if (!subscription) {
                return false;
            }

            // Сохраняем подписку на сервере
            await saveSubscriptionOnServer(subscription);

            // Отправляем тестовое уведомление
            await sendTestPushNotification();

            return true;
        } else {
            // Отписываемся от уведомлений
            return await unsubscribeFromPush();
        }
    } catch (error) {
        console.error('Ошибка при настройке Push-уведомлений:', error);
        return false;
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function () {
    // Находим переключатель push-уведомлений
    const pushToggle = document.querySelector('input[name="push_notifications"]');
    if (pushToggle) {
        // Устанавливаем обработчик изменения состояния
        pushToggle.addEventListener('change', function () {
            setupPushNotifications(this.checked);
        });

        // Проверяем поддержку в браузере
        if (!pushSupported) {
            pushToggle.disabled = true;
            const parentToggleGroup = pushToggle.closest('.toggle-group');
            if (parentToggleGroup) {
                const hint = document.createElement('span');
                hint.className = 'form-hint text-red-500';
                hint.innerHTML = 'Push-уведомления не поддерживаются в вашем браузере';
                parentToggleGroup.appendChild(hint);
            }
        }
    }

    // Добавляем кнопку для отправки тестового уведомления
    const notificationForm = document.getElementById('notification-settings-form');
    if (notificationForm) {
        const pushGroup = notificationForm.querySelector('input[name="push_notifications"]').closest('.form-group');
        if (pushGroup && pushSupported) {
            // Создаем кнопку тестирования
            const testButton = document.createElement('button');
            testButton.type = 'button';
            testButton.id = 'test-push-button';
            testButton.className = 'mt-2 py-1 px-2 bg-blue-500 text-white text-sm rounded hover:bg-blue-600';
            testButton.innerText = 'Отправить тестовое уведомление';
            testButton.style.display = pushToggle.checked ? 'block' : 'none';

            // Добавляем обработчик нажатия
            testButton.addEventListener('click', async function () {
                this.disabled = true;
                this.innerText = 'Отправка...';

                try {
                    const result = await sendTestPushNotification();
                    if (result) {
                        this.className = 'mt-2 py-1 px-2 bg-green-500 text-white text-sm rounded';
                        this.innerText = 'Уведомление отправлено';

                        // Возвращаем исходный стиль через 3 секунды
                        setTimeout(() => {
                            this.className = 'mt-2 py-1 px-2 bg-blue-500 text-white text-sm rounded hover:bg-blue-600';
                            this.innerText = 'Отправить тестовое уведомление';
                            this.disabled = false;
                        }, 3000);
                    } else {
                        this.className = 'mt-2 py-1 px-2 bg-red-500 text-white text-sm rounded';
                        this.innerText = 'Ошибка отправки';

                        setTimeout(() => {
                            this.className = 'mt-2 py-1 px-2 bg-blue-500 text-white text-sm rounded hover:bg-blue-600';
                            this.innerText = 'Отправить тестовое уведомление';
                            this.disabled = false;
                        }, 3000);
                    }
                } catch (error) {
                    console.error(error);
                    this.className = 'mt-2 py-1 px-2 bg-red-500 text-white text-sm rounded';
                    this.innerText = 'Ошибка отправки';

                    setTimeout(() => {
                        this.className = 'mt-2 py-1 px-2 bg-blue-500 text-white text-sm rounded hover:bg-blue-600';
                        this.innerText = 'Отправить тестовое уведомление';
                        this.disabled = false;
                    }, 3000);
                }
            });

            // Показываем/скрываем кнопку при изменении состояния переключателя
            pushToggle.addEventListener('change', function () {
                testButton.style.display = this.checked ? 'block' : 'none';
            });

            // Добавляем кнопку в DOM
            pushGroup.appendChild(testButton);
        }
    }
}); 