# Протокол обмена: сервис ГИБДД ↔ сервис камер (WebSocket)

Транспорт между сервисами — **WebSocket**, не HTTP и не polling.
У каждой камеры **своё** постоянное соединение с сервисом ГИБДД.

```
  Камера CAM-01  ── WS /ws/cameras/CAM-01?token=… ──►  Сервис ГИБДД
  Камера CAM-02  ── WS /ws/cameras/CAM-02?token=… ──►  Сервис ГИБДД
  …
```

## Подключение

```
WS {GIBDD_URL}/ws/cameras/{camera_code}?token={SERVICE_TOKEN}
```

- `camera_code` — код камеры (`CAM-08`)
- `token` — общий секрет `SERVICE_TOKEN`
- при неверном токене соединение закрывается с кодом `4401`
- после accept backend сразу шлёт актуальный `watchlist`

## Сообщения

### Backend → камера

```json
{ "type": "watchlist", "plates": ["А123ВК43", "Е456КМ43"] }
```

```json
{ "type": "ack", "event_id": "…", "status": "accepted", "alert_id": 77, "delivered": true }
```

```json
{ "type": "ack", "event_id": "…", "status": "ignored", "reason": "not_wanted|pending_alert|cooldown|duplicate" }
```

### Камера → backend

```json
{
  "type": "detection",
  "event_id": "9f3c1c7e8a5d4b6f9a2e0d1c3b4a5f67",
  "plate": "А123ВК43",
  "camera_code": "CAM-08",
  "detected_at": "2026-10-12T09:00:00+00:00"
}
```

## Что убрано

- `PUT /v1/watchlist` (HTTP)
- `POST /api/camera-events` (HTTP)

Локальный HTTP сервиса камер: `GET /health`, `GET /v1/cameras`, `GET /v1/watchlist`, `POST /v1/detections` (ручная фиксация; внутри уходит по WS).
