# Сервис камер: отдельный сервис, написанный на стандартной библиотеке Python (зависимостей нет).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONIOENCODING=utf-8

WORKDIR /srv

COPY app ./app

RUN useradd --system --uid 10001 --no-create-home camera
USER camera

EXPOSE 9000

HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=6 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9000/health', timeout=3)"

CMD ["python", "-m", "app.main"]
