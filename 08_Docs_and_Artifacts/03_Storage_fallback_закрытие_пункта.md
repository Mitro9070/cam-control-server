# Закрытие пункта: storage abstraction (postgres + local fallback)

Реализован единый слой хранения `app/storage.py`:

- Режим `postgres`:
  - чтение/сохранение settings через БД,
  - запись событий в `event_log`,
  - health-пинг БД (`SELECT 1`).

- Режим `local`:
  - settings в `LOCAL_STORAGE_PATH/settings.json`,
  - события в `LOCAL_STORAGE_PATH/events.jsonl`.

## Управление режимом
- `STORAGE_MODE=postgres` (основной режим)
- `STORAGE_MODE=local` (fallback)

## Проверка
- Тесты API (`pytest`) проходят: `3 passed`.
- Health в postgres-режиме возвращает `db: connected`.
