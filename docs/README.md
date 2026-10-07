# Материалы по проекту

Здесь лежит то, что относится к проекту в целом. Документация по частям находится рядом с кодом.

| Что | Где |
|---|---|
| Обзор проекта, бизнес-правила, связи между частями | [корневой README](../README.md) |
| ER-диаграмма | [er-diagram.png](er-diagram.png), [er-diagram.svg](er-diagram.svg), исходник [er-diagram.dot](er-diagram.dot) |
| Backend: архитектура, API, база данных, симулятор, настройка, безопасность | [backend/docs/](../backend/docs) |
| Web-frontend: архитектура, страницы и кнопки, поток оповещений, настройка, чек-лист проверки | [web-frontend/docs/](../web-frontend/docs) |

ER-диаграмма построена по `backend/app/models.py`. Чтобы обновить её после изменения моделей, пересоберите `.dot` и выполните `dot -Tpng -Gdpi=170 er-diagram.dot -o er-diagram.png`.
