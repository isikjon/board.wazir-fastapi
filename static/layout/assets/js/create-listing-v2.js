/**
 * Скрипт для страницы создания объявления
 */

// Инициализация переменных вне функций, чтобы избежать рекурсивных вызовов
let uploadedPhotos = 0;
const maxPhotos = 10;

// Загрузка городов из JSON файла
async function loadCities() {
    try {
        const response = await fetch('/static/data/cities.json');
        const data = await response.json();
        
        const citySelect = document.getElementById('city');
        citySelect.innerHTML = '<option value="">Выберите город</option>';
        
        data.regions.forEach(region => {
            // Добавляем группу региона
            const optgroup = document.createElement('optgroup');
            optgroup.label = region.name;
            
            region.cities.forEach(city => {
                const option = document.createElement('option');
                option.value = city;
                option.textContent = city;
                optgroup.appendChild(option);
            });
            
            citySelect.appendChild(optgroup);
        });
    } catch (error) {
        console.error('Ошибка загрузки городов:', error);
    }
}

// Загрузка категорий из БД
async function loadCategories() {
    try {
        const response = await fetch('/api/v1/categories');
        const categories = await response.json();
        
        const categorySelect = document.getElementById('category');
        categorySelect.innerHTML = '<option value="">Выберите категорию</option>';
        
        categories.forEach(category => {
            const option = document.createElement('option');
            option.value = category.id;
            option.textContent = category.name;
            categorySelect.appendChild(option);
        });
    } catch (error) {
        console.error('Ошибка загрузки категорий:', error);
    }
}

$(document).ready(function() {
    console.log('Document ready - New version V2');
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
    
    // Функция загрузки изображений
    function uploadImages(token) {
        return new Promise(function(resolve, reject) {
            // Получаем все загруженные изображения из DOM
            var photoItems = document.querySelectorAll('.photo-item img');
            console.log('Найдено изображений для загрузки:', photoItems.length);
            
            // Если нет изображений, возвращаем пустой массив
            if (photoItems.length === 0) {
                resolve([]);
                return;
            }
            
            // Создаем FormData для загрузки файлов
            var formData = new FormData();
            
            // Теперь мы напрямую получаем данные из DOM элементов
            var imageDataArray = [];
            
            // Массив обещаний для всех операций конвертации URL в File
            var promises = [];
            
            // Функция для преобразования Data URL в File объект
            function dataURLtoFile(dataUrl, filename) {
                return new Promise(function(resolve) {
                    var arr = dataUrl.split(','),
                        mime = arr[0].match(/:(.*?);/)[1],
                        bstr = atob(arr[1]),
                        n = bstr.length,
                        u8arr = new Uint8Array(n);
                    
                    while(n--) {
                        u8arr[n] = bstr.charCodeAt(n);
                    }
                    
                    resolve(new File([u8arr], filename, {type: mime}));
                });
            }
            
            // Собираем все обещания
            for (var i = 0; i < photoItems.length; i++) {
                var img = photoItems[i];
                var src = img.src;
                
                // Если у нас обычный URL (не Data URL), то пропускаем
                if (!src.startsWith('data:')) {
                    // Добавляем URL в массив возвращаемых значений, если это URL сервера
                    if (src.includes('/static/uploads/')) {
                        imageDataArray.push(src);
                    }
                    continue;
                }
                
                // Добавляем обещание в массив
                promises.push(
                    dataURLtoFile(src, 'image_' + i + '.png')
                    .then(function(file) {
                        // Формируем уникальное имя файла
                        return file;
                    })
                );
            }
            
            // Обрабатываем все обещания для конвертации Data URL в File
            Promise.all(promises).then(function(files) {
                // Добавляем все файлы в formData
                files.forEach(function(file, index) {
                    formData.append('files', file);
                    console.log('Добавлен файл для загрузки:', file.name, 'type:', file.type, 'size:', file.size);
                });
                
                // Если у нас нет файлов для загрузки и нет уже загруженных изображений
                if (files.length === 0 && imageDataArray.length === 0) {
                    console.log('Нет файлов для загрузки');
                    resolve([]);
                    return;
                }
                
                // Отправляем файлы на сервер
                $.ajax({
                url: '/api/v1/upload/images/property/',
                type: 'POST',
                data: formData,
                contentType: false,
                processData: false,
                beforeSend: function(xhr) {
                    if (token) {
                        xhr.setRequestHeader('Authorization', 'Bearer ' + token);
                    }
                    console.log('Отправка файлов на сервер...');
                },
                success: function(response) {
                    console.log('Успешный ответ от сервера:', response);
                    
                    // Извлекаем URL изображений из ответа
                    var imageUrls = response.map(function(item) {
                        return item.url;
                    });
                    
                    // Объединяем с уже существующими URL изображений
                    var allImageUrls = imageUrls.concat(imageDataArray);
                    
                    console.log('Полученные URL изображений:', allImageUrls);
                    console.log('Количество загруженных изображений:', allImageUrls.length);
                    resolve(allImageUrls);
                },
                error: function(xhr, status, error) {
                    console.error('Ошибка при загрузке изображений:', error);
                    console.error('Статус:', xhr.status);
                    console.error('Ответ сервера:', xhr.responseText);
                    
                    // Если возникла ошибка загрузки, вернем пустой массив
                    if (xhr.status === 401) {
                        alert('Ошибка авторизации. Пожалуйста, войдите в систему снова.');
                        window.location.href = '/mobile/auth';
                        return;
                    }
                    reject(error);
                }
            });
            }).catch(function(error) {
                console.error('Ошибка при обработке изображений:', error);
                reject(error);
            });
        });
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
            console.log('Validation successful, preparing data');
            
            // Функция для получения cookie
            function getCookie(name) {
                var matches = document.cookie.match(new RegExp(
                    "(?:^|; )" + name.replace(/([\.$?*|{}\\\+^])/g, '\\$1') + "=([^;]*)"
                ));
                return matches ? decodeURIComponent(matches[1]) : undefined;
            }
            
            // Получаем токен авторизации
            var token = getCookie('access_token');
            console.log('Auth token:', token ? 'Found' : 'Not found');
            
            // Показываем индикатор загрузки
            $('#publish-button').prop('disabled', true).text('Загрузка изображений...');
            
            // Сначала загружаем изображения
            uploadImages(token)
                .then(function(imageUrls) {
                    console.log('Изображения загружены:', imageUrls);
                    $('#publish-button').text('Создание объявления...');
                    
                    // Формируем полный адрес
                    var fullAddress = $('#street').val() + ' ' + $('#house-number').val();
                    if ($('#apartment-number').val()) {
                        fullAddress += ', кв. ' + $('#apartment-number').val();
                    }
                    
                    // Определяем ID категории
                    var categoryId = parseInt($('#category').val());
                    
                    // Создаем объект с данными для API
                    var propertyData = {
                        // Основные поля
                        title: $('#title').val() || 'Квартирка хорошая',
                        description: $('#description').val(),
                        price: parseFloat($('#price').val()),
                        address: fullAddress,
                        city: $('#city').val(),
                        area: parseFloat($('#area').val()),
                        
                        // Статус объявления - используем строку вместо Enum
                        status: 'pending',
                        
                        // Категория и тип
                        category_ids: [categoryId],
                        type: $('#property-type').val() || 'apartment',
                        
                        // Дополнительные параметры
                        rooms: parseInt($('.room-btn.active').data('rooms')) || 1,
                        floor: parseInt($('#floor').val()) || 1,
                        building_floors: parseInt($('#total-floors').val()) || 1,
                        
                        // Удобства
                        has_furniture: $('#furniture').is(':checked'),
                        has_balcony: false,
                        has_renovation: $('#refrigerator').is(':checked') || $('#washing-machine').is(':checked'),
                        has_parking: false,
                        
                        // Загруженные URL изображений
                        photo_urls: imageUrls.length > 0 ? imageUrls : [
                            '/static/layout/assets/img/default-property.jpg',
                            '/static/layout/assets/img/default-property-2.jpg'
                        ]
                    };
                    
                    console.log('Prepared property data:', propertyData);
                    
                    // Отправляем данные на сервер
                    $.ajax({
                        url: '/api/v1/properties/',
                        type: 'POST',
                        contentType: 'application/json',
                        data: JSON.stringify(propertyData),
                        beforeSend: function(xhr) {
                            if (token) {
                                xhr.setRequestHeader('Authorization', 'Bearer ' + token);
                            }
                            console.log('Sending data to server');
                        },
                        success: function(response) {
                            console.log('Success response:', response);
                            alert('Объявление успешно создано и отправлено на модерацию!');
                            window.location.href = '/mobile/profile';
                        },
                        error: function(xhr, status, error) {
                            console.error('Error creating property:');
                            console.error('Status:', xhr.status);
                            console.error('Error text:', error);
                            console.error('Server response:', xhr.responseText);
                            
                            try {
                                var errorResponse = JSON.parse(xhr.responseText);
                                console.error('Error details:', errorResponse);
                                
                                if (xhr.status === 401) {
                                    alert('Ошибка авторизации. Пожалуйста, войдите в систему снова.');
                                    window.location.href = '/mobile/auth';
                                    return;
                                }
                                
                                if (errorResponse.detail && Array.isArray(errorResponse.detail)) {
                                    const errors = errorResponse.detail.map(item => 
                                        `Ошибка в поле "${item.loc.join('.')}" - ${item.msg}`
                                    ).join('\n');
                                    alert(`Произошли следующие ошибки:\n${errors}`);
                                } else {
                                    alert('Произошла ошибка при создании объявления. Пожалуйста, попробуйте позже.');
                                }
                            } catch (e) {
                                console.error('Error parsing server response:', e);
                                alert('Произошла ошибка при создании объявления. Пожалуйста, попробуйте позже.');
                            }
                            
                            $('#publish-button').prop('disabled', false).text('Опубликовать объявление');
                        }
                    });
                })
                .catch(function(error) {
                    console.error('Ошибка при загрузке изображений:', error);
                    alert('Ошибка при загрузке изображений. Пожалуйста, попробуйте позже.');
                    $('#publish-button').prop('disabled', false).text('Опубликовать объявление');
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

    // Загружаем данные
    loadCities();
    loadCategories();
});
