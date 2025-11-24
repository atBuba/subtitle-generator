# Используем официальный образ Python 3.11
FROM python:3.11-slim

# Устанавливаем необходимые системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем requirements.txt и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код приложения
COPY . .

# Создаем директорию для медиафайлов
RUN mkdir -p subtitle_generator_app/media

# Создаем директорию для базы данных SQLite
RUN mkdir -p db

# Экспортируем переменные окружения по умолчанию
ENV PYTHONPATH=/app
ENV DJANGO_SETTINGS_MODULE=subtitle_generator.settings

# Собираем статические файлы
# RUN python subtitle_generator/manage.py collectstatic --noinput

# Открываем порт
EXPOSE 8000

# Запускаем миграции и сервер
CMD ["sh", "-c", "python subtitle_generator/manage.py migrate --run-syncdb && python subtitle_generator/manage.py runserver 0.0.0.0:8000"]