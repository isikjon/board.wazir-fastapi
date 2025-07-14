/**
 * Скрипт для страницы создания объявления
 */

// Инициализация переменных вне функций, чтобы избежать рекурсивных вызовов
let uploadedPhotos = 0;
const maxPhotos = 10;

$(document).ready(function() {
    console.log('Document ready');
    // Инициализация счетчика символов для описания
    $('#description').on('input', function() {
        const maxLength = 2000;
        const currentLength = $(this).val().length;
        $('#description-counter').text(currentLength + '/' + maxLength);
        
        if (currentLength > maxLength) {
            $('#description-counter').addClass('error');
            $(this).val($(this).val().substring(0, maxLength));
        } else {
            $('#description-counter').removeClass('error');
        }
    });
    
    // Обработка кнопок выбора количества комнат
    $('.room-btn').on('click', function() {
        $('.room-btn').removeClass('active');
        $(this).addClass('active');
    });
    
    // Обработка клика на область загрузки фотографий
    document.getElementById('photo-upload-trigger').onclick = function() {
        document.getElementById('photo-upload').click();
    };
    
    // Обработка загрузки фотографий
    document.getElementById('photo-upload').onchange = function(e) {
        var files = e.target.files;
        
        if (files && files.length > 0) {
            // Проверяем, не превышено ли максимальное количество фото
            if (uploadedPhotos + files.length > maxPhotos) {
                alert('Максимальное количество фотографий: ' + maxPhotos);
                return;
            }
            
            // Используем setTimeout для предотвращения переполнения стека
            setTimeout(function() {
                handleFiles(files);
            }, 0);
        }
    };
    
    // Обработка всех файлов без рекурсии
    function handleFiles(files) {
        var uploadedPhotosContainer = document.getElementById('uploaded-photos');
        
        for (var i = 0; i < files.length; i++) {
            var file = files[i];
            if (!file.type.match('image.*')) {
                continue;
            }
            
            (function(file) {
                var reader = new FileReader();
                
                reader.onload = function(e) {
                    // Создаем элементы DOM напрямую, без jQuery
                    var photoItem = document.createElement('div');
                    photoItem.className = 'photo-item';
                    
                    var img = document.createElement('img');
                    img.src = e.target.result;
                    img.alt = 'Uploaded photo';
                    photoItem.appendChild(img);
                    
                    var removeBtn = document.createElement('div');
                    removeBtn.className = 'photo-remove';
                    
                    var icon = document.createElement('i');
                    icon.className = 'fas fa-times';
                    removeBtn.appendChild(icon);
                    
                    // Добавляем обработчик клика напрямую
                    removeBtn.onclick = function() {
                        photoItem.remove();
                        uploadedPhotos--;
                        
                        // Показываем сообщение об ошибке, если фотографий недостаточно
                        if (uploadedPhotos < 2) {
                            document.querySelector('.photo-validation-error').classList.remove('hidden');
                        }
                    };
                    
                    photoItem.appendChild(removeBtn);
                    uploadedPhotosContainer.appendChild(photoItem);
                    
                    uploadedPhotos++;
                    
                    // Скрываем сообщение об ошибке, если фотографий достаточно
                    if (uploadedPhotos >= 2) {
                        document.querySelector('.photo-validation-error').classList.add('hidden');
                    }
                };
                
                reader.readAsDataURL(file);
            })(file);
        }
    }
    
    // Удаление фотографий (для уже существующих элементов)
    document.addEventListener('click', function(e) {
        if (e.target && (e.target.matches('.photo-remove i') || e.target.matches('.photo-remove'))) {
            var photoItem = e.target.closest('.photo-item');
            if (photoItem) {
                photoItem.remove();
                uploadedPhotos--;
                
                // Показываем сообщение об ошибке, если фотографий недостаточно
                if (uploadedPhotos < 2) {
                    document.querySelector('.photo-validation-error').classList.remove('hidden');
                }
            }
        }
    });
    
    // Валидация формы при отправке
    $('#create-listing-form').on('submit', function(e) {
        e.preventDefault();
        let isValid = true;
        
        // Валидация фотографий
        if (uploadedPhotos < 2) {
            $('.photo-validation-error').removeClass('hidden');
            isValid = false;
        }
        
        // Валидация категории
        if (!$('#category').val()) {
            $('.category-validation-error').removeClass('hidden');
            isValid = false;
        } else {
            $('.category-validation-error').addClass('hidden');
        }
        
        // Валидация типа недвижимости
        if (!$('#property-type').val()) {
            $('.property-type-validation-error').removeClass('hidden');
            isValid = false;
        } else {
            $('.property-type-validation-error').addClass('hidden');
        }
        
        // Валидация города
        if (!$('#city').val()) {
            $('.city-validation-error').removeClass('hidden');
            isValid = false;
        } else {
            $('.city-validation-error').addClass('hidden');
        }
        
        // Валидация улицы
        if (!$('#street').val()) {
            $('.street-validation-error').removeClass('hidden');
            isValid = false;
        } else {
            $('.street-validation-error').addClass('hidden');
        }
        
        // Валидация номера дома
        if (!$('#house-number').val()) {
            $('.house-number-validation-error').removeClass('hidden');
            isValid = false;
        } else {
            $('.house-number-validation-error').addClass('hidden');
        }
        
        // Валидация количества комнат
        if (!$('.room-btn.active').length) {
            $('.rooms-validation-error').removeClass('hidden');
            isValid = false;
        } else {
            $('.rooms-validation-error').addClass('hidden');
        }
        
        // Валидация площади
        if (!$('#area').val()) {
            $('.area-validation-error').removeClass('hidden');
            isValid = false;
        } else {
            $('.area-validation-error').addClass('hidden');
        }
        
        // Валидация этажа
        if (!$('#floor').val()) {
            $('.floor-validation-error').removeClass('hidden');
            isValid = false;
        } else {
            $('.floor-validation-error').addClass('hidden');
        }
        
        // Валидация общего количества этажей
        if (!$('#total-floors').val()) {
            $('.total-floors-validation-error').removeClass('hidden');
            isValid = false;
        } else {
            $('.total-floors-validation-error').addClass('hidden');
        }
        
        // Валидация цены
        if (!$('#price').val()) {
            $('.price-validation-error').removeClass('hidden');
            isValid = false;
        } else {
            $('.price-validation-error').addClass('hidden');
        }
        
        // Валидация описания
        if (!$('#description').val() || $('#description').val().length < 50) {
            $('.description-validation-error').removeClass('hidden');
            isValid = false;
        } else {
            $('.description-validation-error').addClass('hidden');
        }
        
        if (isValid) {
            // Получение JWT токена из cookies
            function getCookie(name) {
                var matches = document.cookie.match(new RegExp(
                    "(?:^|; )" + name.replace(/([\.$?*|{}\\\/\+^])/g, '\\$1') + "=([^;]*)"
                ));
                return matches ? decodeURIComponent(matches[1]) : undefined;
            }
            
            // Получаем токен из cookie - в этом приложении токен хранится в cookie 'access_token'
            var token = getCookie('access_token');
            console.log('Токен авторизации:', token ? 'Найден' : 'Не найден');
            
            // 1. Сначала загрузим все фотографии и получим их URL
            // Собираем все файлы изображений с DOM
            var photoFiles = [];
            $('.photo-item').each(function() {
                var imgSrc = $(this).find('img').attr('src');
                // Проверяем, является ли источник файлом или URL
                if (imgSrc && imgSrc.startsWith('data:')) {
                    // Это файл, преобразуем base64 обратно в файл
                    var dataURI = imgSrc;
                    var byteString = atob(dataURI.split(',')[1]);
                    var mimeString = dataURI.split(',')[0].split(':')[1].split(';')[0];
                    var ab = new ArrayBuffer(byteString.length);
                    var ia = new Uint8Array(ab);
                    
                    for (var i = 0; i < byteString.length; i++) {
                        ia[i] = byteString.charCodeAt(i);
                    }
                    
                    var blob = new Blob([ab], {type: mimeString});
                    var fileName = 'image_' + Date.now() + '_' + Math.floor(Math.random() * 1000) + '.jpg';
                    var file = new File([blob], fileName, {type: mimeString});
                    photoFiles.push(file);
                }
            });
            
            if (photoFiles.length < 2) {
                alert('Пожалуйста, загрузите как минимум 2 фотографии');
                return;
            }
            
            // Создаем FormData для загрузки файлов
            var uploadFormData = new FormData();
            photoFiles.forEach(function(file, index) {
                uploadFormData.append('files', file);
            });
            
            // Показываем индикатор загрузки
            $('#publish-button').prop('disabled', true).text('Загрузка изображений...');
            
            // Загружаем изображения
            $.ajax({
                url: '/api/v1/upload/images/property/',
                type: 'POST',
                data: uploadFormData,
                contentType: false,
                processData: false,
                beforeSend: function(xhr) {
                    if (token) {
                        xhr.setRequestHeader('Authorization', 'Bearer ' + token);
                    }
                },
                success: function(uploadResponse) {
                    console.log('Изображения успешно загружены:', uploadResponse);
                    
                    // 2. После успешной загрузки фотографий создаем объявление
                    var photoUrls = uploadResponse.map(function(item) {
                        return item.url;
                    });
                    
                    // Преобразуем значения из формы в правильный формат
                    var categoryValue = $('#category').val();
                    var propertyTypeValue = $('#property-type').val();
                    
                    // Определим ID категории на основе выбора продажа/аренда
                    var categoryIds = [];
                    if (categoryValue === 'sale') {
                        categoryIds.push(1); // ID для категории "Продажа"
                    } else if (categoryValue === 'rent') {
                        categoryIds.push(2); // ID для категории "Аренда"
                    }
                    
                    // Формируем полный адрес
                    var fullAddress = $('#street').val() + ' ' + $('#house-number').val();
                    if ($('#apartment-number').val()) {
                        fullAddress += ', кв. ' + $('#apartment-number').val();
                    }
                    
                    // Собираем данные формы с правильными именами полей
                    var formData = {
                        photo_urls: photoUrls,
                        title: $('#title').val(),
                        description: $('#description').val(),
                        price: parseFloat($('#price').val()),
                        category_ids: categoryIds,
                        address: fullAddress,
                        city: $('#city').val(),
                        area: parseFloat($('#area').val()),
                        status: 'pending', // Используем допустимое значение из enum
                        type: propertyTypeValue || 'apartment',
                        rooms: parseInt($('.room-btn.active').data('rooms')) || 1,
                        floor: parseInt($('#floor').val()) || 1,
                        building_floors: parseInt($('#total-floors').val()) || 1,
                        has_furniture: $('#furniture').is(':checked'),
                        has_balcony: false,
                        has_renovation: $('#refrigerator').is(':checked') || $('#washing-machine').is(':checked'),
                        has_parking: false,
                    };
                    
                    // Выводим данные для отладки
                    console.log('Подготовленные данные для отправки:', formData);
                    
                    // Изменяем текст кнопки
                    $('#publish-button').text('Создание объявления...');
                    
                    // Отправляем данные объявления
                    $.ajax({
                        url: '/api/v1/properties',
                        type: 'POST',
                        contentType: 'application/json',
                        data: JSON.stringify(formData),
                        beforeSend: function(xhr) {
                            if (token) {
                                xhr.setRequestHeader('Authorization', 'Bearer ' + token);
                            }
                            console.log('Отправка данных объявления:', JSON.stringify(formData));
                        },
                        success: function(response) {
                            console.log('Объявление успешно создано:', response);
                            alert('Объявление успешно создано и отправлено на модерацию!');
                            window.location.href = '/mobile/profile';
                        },
                        error: function(xhr, status, error) {
                            console.error('Ошибка при создании объявления:', status, error);
                            console.error('Ответ сервера:', xhr.responseText);
                            
                            try {
                                var errorResponse = JSON.parse(xhr.responseText);
                                console.error('Детали ошибки:', errorResponse);
                                
                                if (xhr.status === 401) {
                                    alert('Ошибка авторизации. Пожалуйста, войдите в систему снова.');
                                    window.location.href = '/mobile/auth';
                                    return;
                                }
                                
                                alert('Ошибка при создании объявления: ' + errorResponse.detail);
                            } catch (e) {
                                alert('Произошла ошибка при создании объявления. Пожалуйста, попробуйте позже.');
                            }
                            
                            $('#publish-button').prop('disabled', false).text('Опубликовать объявление');
                        }
                    });
                },
                error: function(xhr, status, error) {
                    console.error('Ошибка при загрузке изображений:', status, error);
                    alert('Ошибка при загрузке изображений. Пожалуйста, попробуйте снова.');
                    $('#publish-button').prop('disabled', false).text('Опубликовать объявление');
                }
            });
        } else {
            // Прокручиваем к первой ошибке
            $('html, body').animate({
                scrollTop: $('.text-red-500:not(.hidden)').first().offset().top - 100
            }, 500);
        }
    });

    // Загружаем данные о погоде и курсе валют
    getWeather();
    getCurrencyRate();
});
