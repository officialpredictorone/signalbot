# 1. Базовый образ Python
FROM python:3.11-slim

# 2. Устанавливаем зависимости системы (если aiogram или боту что-то нужно)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 3. Устанавливаем рабочую директорию
WORKDIR /app

# 4. Копируем файлы проекта
COPY . .

# 5. Устанавливаем Python-зависимости
RUN pip install --no-cache-dir -r requirements.txt

# 6. Указываем команду запуска
CMD ["python", "main.py"]
