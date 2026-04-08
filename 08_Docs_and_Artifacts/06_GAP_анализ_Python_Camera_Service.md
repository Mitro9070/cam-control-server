# Актуальный GAP-анализ: Python Camera Service vs ТР (`техническое-решение-greateyes`)

Дата актуализации: 2026-03-08  
Основание: сверка документов из `техническое-решение-greateyes` с текущим кодом/артефактами в репозитории.  
Важно: в этом обновлении **не выполнялись новые прогоны**, только анализ фактической реализации и уже зафиксированных артефактов/логики.

## 1) Что уже совпадает с ТР
- Реализована целевая связка `ASCOM Local Server -> Python service -> SDK`, Python API живет в `FastAPI` (`/api/v1`), UI доступен через `/ui`.
- Реализованы ключевые сценарии API: `connect/disconnect`, `state/capabilities`, `exposures start/status/abort/stop`, `latest image`, `cooling`, `warmup`, `settings`, `logs`.
- Есть `local/postgres` storage mode, миграции `Alembic`, базовые таблицы `app_settings` и `event_log`.
- В `native` режиме реализованы сетевые шаги SDK (`SetupCameraInterface`, `ConnectTo*Server`, `ConnectCamera`, `InitCamera`) и fallback-ветки.
- Реализован warm-up как отдельный job со статусом.

## 2) Актуальные GAP (по приоритету)

1. **Стабильность native connect в runtime**
   - В `sdk_adapter.py` усилена стабилизация: сериализация SDK-вызовов через lock + увеличенные retry/backoff + unlock sequence.
   - Практический риск аппаратных интермиттентов полностью не исключен и требует длительной валидации на железе.
   - Статус: `Partially Closed`.

2. **Бизнес-правило охлаждения в level-mode зафиксировано, требуется только эксплуатационная валидация**
   - Формализованное правило описано в `техническое-решение-greateyes/01_ТР_GreatEyes_ASCOM_Python_PostgreSQL.md` (раздел `7.3.1`).
   - В коде используется детерминированный линейный маппинг `target_temp_c -> level` в виртуальном диапазоне `[-80; +20]` с clamp.
   - Статус: `Partially Closed` (описание + код закрыты, остается длительная hardware-валидация).

3. **API-контракты ТР и текущая реализация**
   - Добавлен `percent` в `GET /camera/exposures/{id}/status`.
   - Добавлен путь `GET /camera/cooling/warmup/{id}/status` (при сохранении совместимости с `.../warmup/{id}`).
   - Контракт `as-built` зафиксирован в `техническое-решение-greateyes/02_Контракты_API_и_методы.md`.
   - Статус: `Closed`.

4. **Wire-format изображения для C# `ImageArray`**
   - Добавлен endpoint `GET /camera/images/latest/raw` (`application/octet-stream`) с метаданными в headers.
   - C# адаптер использует raw endpoint как основной и JSON как fallback.
   - Контракт зафиксирован в `техническое-решение-greateyes/02_Контракты_API_и_методы.md`.
   - Статус: `Closed`.

5. **Операционная модель БД**
   - Добавлена миграция `20260308_0002_operational_tables` с таблицами:
     - `camera_profiles`
     - `camera_session`
     - `exposure_job`
     - `exposure_image_meta`
   - Добавлена запись lifecycle в storage/repository для postgres-режима.
   - Статус: `Closed` для scope R1.1.

6. **Тестовое покрытие**
   - Добавлен C# unit test проект `ASCOM.ProjectR1.Camera.Tests`.
   - Python тесты расширены под новые контракты (`percent`, raw image endpoint, warmup status path).
   - Регулярный длительный hardware soak остается эксплуатационной задачей.
   - Статус: `Partially Closed`.

## 3) Что больше не является актуальным GAP
- Устаревший тезис «рабочий контур в основном mock» более неактуален: `native` путь реализован и эксплуатируется, но остается риск по стабильности `camera busy`.
- Базовый API-каркас/SDK-обвязка/охлаждение/warm-up уже не на уровне заготовки, а на уровне работающего контура с открытыми вопросами hardening.

## 4) Консолидированный список до закрытия GAP
- [ ] Подтвердить на длительном hardware-soak, что `camera busy` устранен как эксплуатационный дефект.
- [ ] Подтвердить на длительном hardware-прогоне корректность нового маппинга `target_temp_c -> level` в level-mode.
- [x] Зафиксировать финальный API-контракт `as-built` (включая решение по `percent` и финальный путь warm-up status).
- [x] Зафиксировать финальный wire-format изображения для C# `ImageArray`.
- [x] Расширить схему БД до целевого состава R1.1 (`camera_session`, `exposure_job`, `exposure_image_meta`, `camera_profiles`).
- [ ] Закрыть приемочный минимум тестов и зафиксировать итоговый Go/No-Go отчет (длительный hardware-soak).

## 5) Вывод
- Для текущего этапа интеграции (продолжение работ по C#/операционному контуру) проект находится в рабочем состоянии.
- Главные незакрытые разрывы сейчас: **устойчивость native-сессии SDK** и **формализация бизнес-правила охлаждения в level-mode**.
- Этот документ заменяет предыдущую версию GAP и отражает текущее состояние «as-is».
