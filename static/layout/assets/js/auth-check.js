// Удаляю весь код, который создает и добавляет user-panel

document.addEventListener('DOMContentLoaded', function () {
    // Проверяем, есть ли токен авторизации
    const token = localStorage.getItem('access_token');

    if (!token) {
        // Если нет токена, перенаправляем на страницу авторизации
        window.location.href = '/mobile/auth';
        return;
    }

    // Глобальный ajaxSetup закомментирован, чтобы не было конфликтов с локальными headers
    // $.ajaxSetup({
    //     beforeSend: function(xhr) {
    //         xhr.setRequestHeader('Authorization', 'Bearer ' + token);
    //     }
    // });

    // Не добавляем панель пользователя на главной странице
    if (window.location.pathname === '/mobile' || window.location.pathname === '/mobile/') {
        return;
    }
}); 