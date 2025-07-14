FROM python:3.12-slim

WORKDIR /app

# Установка необходимых системных зависимостей
RUN apt-get update && apt-get install -y \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Копируем файлы зависимостей
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем все файлы проекта
COPY . .

# Создаем директории для медиа-файлов если их нет
RUN mkdir -p media

# Делаем entrypoint скрипт исполняемым
RUN chmod +x /app/entrypoint.sh

# Открываем порт для приложения
EXPOSE 8000

# Устанавливаем entrypoint скрипт
ENTRYPOINT ["/app/entrypoint.sh"]

# Команда для запуска приложения
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
