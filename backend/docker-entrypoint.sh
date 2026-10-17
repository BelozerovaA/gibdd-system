#!/bin/sh
# Запуск сервиса ГИБДД в контейнере: дождаться базы, заполнить её (один раз), запустить сервер.
set -e

echo "Жду базу данных..."
attempt=0
until python -c "from app.database import engine; engine.connect().close()" 2>/dev/null; do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge 60 ]; then
        echo "База данных не отвечает. Последняя ошибка:"
        python -c "from app.database import engine; engine.connect()"
        exit 1
    fi
    sleep 2
done
echo "База данных доступна."

# seed.py безопасно запускать повторно: существующие записи не дублируются.
if [ "${RUN_SEED:-1}" = "1" ]; then
    python seed.py
fi

exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
