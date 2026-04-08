# 02_Python_Camera_Service

Зона реализации Python camera-service:
- API,
- доменная логика,
- orchestration экспозиций,
- интеграция со storage.

## Текущий статус
- Этап 1 стартован.
- Каркас сервиса развернут.
- Бэкенд проектируется с подключением к PostgreSQL с первого этапа.
- Реализован слой хранения с режимами `postgres` и `local` (fallback).

## Быстрый запуск
1. Создать локальный `.env` на основе `.env.example`.
2. Указать фактическое имя БД в `DB_DATABASE`.
3. Выбрать режим хранения:
   - `STORAGE_MODE=postgres` (основной)
   - `STORAGE_MODE=local` (fallback)
3. Установить зависимости:
   - `python -m pip install -e .`
4. Применить миграции:
   - `alembic upgrade head`
5. Запустить сервис:
   - `uvicorn app.main:app --host 127.0.0.1 --port 3037`

## Базовые endpoints
- `GET /api/v1/health`
- `POST /api/v1/camera/connect`
- `POST /api/v1/camera/disconnect`
- `PUT /api/v1/camera/config/roi-binning`
- `POST /api/v1/camera/exposures`
- `GET /api/v1/camera/exposures/{id}/status`
- `POST /api/v1/camera/exposures/{id}/abort`
- `POST /api/v1/camera/exposures/{id}/stop`
- `GET /api/v1/camera/images/latest`
- `PUT /api/v1/camera/cooling/power`
- `PUT /api/v1/camera/cooling/target`
- `GET /api/v1/camera/cooling/status`
- `POST /api/v1/camera/cooling/warmup`
- `GET /api/v1/camera/cooling/warmup/{id}`
- `GET /api/v1/settings`
- `PUT /api/v1/settings`
- `GET /api/v1/camera/state`
- `GET /api/v1/camera/capabilities`
