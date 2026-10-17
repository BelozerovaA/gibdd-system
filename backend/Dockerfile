# Сервис ГИБДД (backend): FastAPI + SQLAlchemy.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONIOENCODING=utf-8 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Сначала зависимости: этот слой пересобирается, только если изменился requirements.txt
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Скрипт запуска мог получить Windows-переводы строк (CRLF) при клонировании: убираем их,
# иначе Linux не найдёт интерпретатор «sh\r».
RUN sed -i 's/\r$//' docker-entrypoint.sh && chmod +x docker-entrypoint.sh \
    && useradd --system --uid 10001 --no-create-home app \
    && chown -R app /app
USER app

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=6 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/', timeout=3)"

ENTRYPOINT ["./docker-entrypoint.sh"]
