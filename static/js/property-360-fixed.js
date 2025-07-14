$(document).ready(function() {
    // Обработчик клика по кнопке загрузки 360°
    $('.upload-360-btn').on('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        
        const propertyId = $(this).data('property-id');
        $('#property-id-for-360').val(propertyId);
        $('#upload-360-modal').removeClass('hidden');
        
        // Получаем текущие данные 360° для объявления через AJAX
        $.ajax({
            url: `/api/v1/properties/${propertyId}/360`,
            method: 'GET',
            beforeSend: function(xhr) {
                // Пробуем получить токен из разных источников
                let token = getCookie('access_token');
                
                // Если токена нет в cookie, проверяем в localStorage
                if (!token && window.localStorage) {
                    token = localStorage.getItem('access_token');
                }
                
                // Если токена нет в localStorage, проверяем в sessionStorage
                if (!token && window.sessionStorage) {
                    token = sessionStorage.getItem('access_token');
                }
                
                if (token) {
                    xhr.setRequestHeader('Authorization', `Bearer ${token}`);
                    console.log('Токен авторизации найден и добавлен в заголовок');
                } else {
                    // В крайнем случае, пытаемся получить токен из документа
                    const adminTokenInput = document.getElementById('admin-token');
                    if (adminTokenInput && adminTokenInput.value) {
                        xhr.setRequestHeader('Authorization', `Bearer ${adminTokenInput.value}`);
                        console.log('Токен взят из скрытого поля admin-token');
                    } else {
                        console.warn('Токен авторизации не найден');
                    }
                }
            },
            success: function(response) {
                if (response.tour_360_url) {
                    $('#tour-360-url').val(response.tour_360_url);
                }
                if (response.notes) {
                    $('#tour-360-date').val(response.notes);
                }
            },
            error: function(error) {
                console.error('Ошибка при получении данных 360°:', error);
                // Показываем подробности ошибки
                if (error.responseJSON && error.responseJSON.detail) {
                    alert('Ошибка: ' + error.responseJSON.detail);
                } else {
                    alert('Произошла ошибка при получении данных 360°. Проверьте консоль для деталей.');
                }
            }
        });
    });
    
    // Закрытие модального окна загрузки 360°
    $('.close-upload-360-modal, #upload-360-modal-backdrop').on('click', function() {
        $('#upload-360-modal').addClass('hidden');
    });
    
    // Сохранение данных 360°
    $('#save-360-btn').on('click', function() {
        const propertyId = $('#property-id-for-360').val();
        const tourUrl = $('#tour-360-url').val();
        const tourDate = $('#tour-360-date').val();
        
        // Проверяем, что URL заполнен
        if (!tourUrl) {
            alert('Пожалуйста, укажите URL 360° панорамы');
            return;
        }
        
        // Отправляем данные на сервер
        $.ajax({
            url: `/api/v1/properties/${propertyId}/360`,
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                tour_360_url: tourUrl,
                notes: tourDate
            }),
            beforeSend: function(xhr) {
                // Пробуем получить токен из разных источников
                let token = getCookie('access_token');
                
                // Если токена нет в cookie, проверяем в localStorage
                if (!token && window.localStorage) {
                    token = localStorage.getItem('access_token');
                }
                
                // Если токена нет в localStorage, проверяем в sessionStorage
                if (!token && window.sessionStorage) {
                    token = sessionStorage.getItem('access_token');
                }
                
                if (token) {
                    xhr.setRequestHeader('Authorization', `Bearer ${token}`);
                    console.log('Токен авторизации найден и добавлен в заголовок');
                } else {
                    // В крайнем случае, пытаемся получить токен из документа
                    const adminTokenInput = document.getElementById('admin-token');
                    if (adminTokenInput && adminTokenInput.value) {
                        xhr.setRequestHeader('Authorization', `Bearer ${adminTokenInput.value}`);
                        console.log('Токен взят из скрытого поля admin-token');
                    } else {
                        console.warn('Токен авторизации не найден');
                    }
                }
                
                // Добавляем X-CSRF-Token для защиты от CSRF
                const csrfToken = getCookie('csrftoken') || $('meta[name="csrf-token"]').attr('content');
                if (csrfToken) {
                    xhr.setRequestHeader('X-CSRF-Token', csrfToken);
                }
            },
            success: function(response) {
                $('#upload-360-modal').addClass('hidden');
                
                // Обновляем статус 360° в таблице без перезагрузки страницы
                const row = $(`tr[data-id="${propertyId}"]`);
                row.find('td:nth-child(7)').html('<span class="px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800">Есть</span>');
                
                alert('Данные 360° успешно сохранены!');
            },
            error: function(error) {
                console.error('Ошибка при сохранении данных 360°:', error);
                
                // Показываем подробности ошибки
                if (error.responseJSON && error.responseJSON.detail) {
                    alert('Ошибка: ' + error.responseJSON.detail);
                } else {
                    alert('Произошла ошибка при сохранении данных. Пожалуйста, попробуйте еще раз.');
                }
            }
        });
    });
    
    // Функция для получения cookie по имени
    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return null;
    }
});
