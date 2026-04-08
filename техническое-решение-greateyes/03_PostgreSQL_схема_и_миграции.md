# PostgreSQL: схема, подключение и миграции

## 0. Позиционирование по релизам
- **R1:** PostgreSQL не является обязательной зависимостью (service может работать с локальным storage).
- **R1.1:** PostgreSQL включается как штатное хранилище операционных данных.
- От PostgreSQL не отказываемся; переносим жесткую зависимость из первого запуска в следующий этап.

## 1. Подключение к БД
Креды будут предоставлены отдельно. Конфигурация через env vars:

- `DB_HOST`
- `DB_PORT` (default `5432`)
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_SSLMODE` (`disable|prefer|require|verify-ca|verify-full`)
- `DB_POOL_SIZE` (default `10`)
- `DB_POOL_MAX_OVERFLOW` (default `20`)

Пример DSN:
`postgresql+psycopg://<user>:<pass>@<host>:<port>/<db>?sslmode=<sslmode>`

## 2. Что храним в БД (этап 1.1)
- Глобальные настройки сервиса.
- Профили камеры (предустановки съемки).
- Сессии подключения камеры.
- Технические метаданные экспозиций.
- Журнал событий и ошибок.
- В БД не храним научные данные наблюдений: названия объектов, научные каталоги, FITS-файлы.

## 3. Логическая схема
## 3.1 Таблицы
- `app_settings` — ключ-значение параметров.
- `camera_profiles` — пользовательские/операторские профили съемки.
- `camera_session` — подключение/отключение, версия SDK, хост.
- `exposure_job` — lifecycle экспозиции.
- `exposure_image_meta` — только технические параметры/метаданные кадра.
- `event_log` — события/ошибки и трассировка.

## 3.2 SQL DDL (базовая миграция)
```sql
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS app_settings (
  key               text PRIMARY KEY,
  value_json        jsonb NOT NULL,
  updated_at        timestamptz NOT NULL DEFAULT now(),
  updated_by        text
);

CREATE TABLE IF NOT EXISTS camera_profiles (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name              text NOT NULL UNIQUE,
  is_default        boolean NOT NULL DEFAULT false,
  readout_speed     integer NOT NULL,
  gain_mode         text NOT NULL,
  cooler_level      integer,
  target_temp_c     integer,
  bin_x             integer NOT NULL DEFAULT 1,
  bin_y             integer NOT NULL DEFAULT 1,
  num_x             integer,
  num_y             integer,
  start_x           integer NOT NULL DEFAULT 0,
  start_y           integer NOT NULL DEFAULT 0,
  exposure_sec      numeric(10,3),
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS camera_session (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  camera_index      integer NOT NULL DEFAULT 0,
  model_id          integer,
  model_name        text,
  sdk_version       text,
  host_name         text,
  connected_at      timestamptz NOT NULL,
  disconnected_at   timestamptz,
  status            text NOT NULL,
  error_message     text
);

CREATE TABLE IF NOT EXISTS exposure_job (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id        uuid REFERENCES camera_session(id),
  profile_id        uuid REFERENCES camera_profiles(id),
  requested_at      timestamptz NOT NULL DEFAULT now(),
  started_at        timestamptz,
  finished_at       timestamptz,
  duration_sec      numeric(10,3) NOT NULL,
  light_frame       boolean NOT NULL,
  state             text NOT NULL,
  error_code        text,
  error_message     text
);

CREATE TABLE IF NOT EXISTS exposure_image_meta (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  exposure_id       uuid NOT NULL REFERENCES exposure_job(id) ON DELETE CASCADE,
  width             integer NOT NULL,
  height            integer NOT NULL,
  bit_depth         integer NOT NULL DEFAULT 16,
  pixel_type        text NOT NULL DEFAULT 'uint16',
  orientation       text NOT NULL DEFAULT 'top_left_origin',
  bin_x             integer NOT NULL,
  bin_y             integer NOT NULL,
  start_x           integer NOT NULL,
  start_y           integer NOT NULL,
  created_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS event_log (
  id                bigserial PRIMARY KEY,
  event_time        timestamptz NOT NULL DEFAULT now(),
  level             text NOT NULL,
  source            text NOT NULL,
  event_type        text NOT NULL,
  correlation_id    text,
  payload_json      jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_event_log_event_time ON event_log(event_time DESC);
CREATE INDEX IF NOT EXISTS idx_event_log_correlation_id ON event_log(correlation_id);
CREATE INDEX IF NOT EXISTS idx_exposure_job_requested_at ON exposure_job(requested_at DESC);
CREATE INDEX IF NOT EXISTS idx_exposure_job_state ON exposure_job(state);
```

## 4. Миграции
## 4.1 Инструмент
- `Alembic` (Python) как основной инструмент versioned migrations.

## 4.2 Политика миграций
- Каждая миграция атомарна и обратима (`upgrade`/`downgrade`).
- Любое изменение схемы только через PR.
- Перед merge обязателен прогон миграций на тестовой БД.

## 4.3 Структура ревизий (пример)
- `0001_initial_schema`
- `0002_add_unique_default_profile_constraint`
- `0003_add_retention_fields`

## 5. Дополнительные требования
- Retention policy:
  - `event_log`: хранить 90 дней (настройка).
  - `exposure_job/meta`: хранить 1 год (настройка).
- Очистка по cron/job в Python service.

## 6. Что еще хранить на этапе 1.1
- Конфигурация портов API.
- Feature flags (`enable_mock_sdk`, `strict_conform_mode`).
- Runtime limits (`max_parallel_requests`, `sdk_call_timeout_ms`).

## 7. Безопасность
- Пароли не хранятся в репозитории.
- Подключение по least privilege пользователю БД.
- Если БД не локально — включить SSL и ограничить сеть.
