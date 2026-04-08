# Техническое решение (ТР): GreatEyes ASCOM Integration Platform

## 1. Цель документа
Документ описывает полное техническое решение для интеграции камер GreatEyes в ASCOM-экосистему через архитектуру:

`ASCOM Local Server (C#)` -> `Python camera-service` -> `GreatEyes SDK/DLL`.

Дополнительно описаны:
- бизнес-процесс эксплуатации,
- хранение настроек и операционных данных (локально + PostgreSQL),
- миграции БД,
- UI для проверки и обслуживания,
- тестирование и автотесты.

## 2. Бизнес-задача
### 2.1 Проблема
- Камера GreatEyes не имеет готового ASCOM-драйвера для текущих сценариев эксплуатации.
- В обсерватории используется ASCOM-совместимый стек, поэтому устройство должно быть доступно как стандартная ASCOM-камера.

### 2.2 Цель внедрения
- Обеспечить совместимость GreatEyes с ASCOM-софтом (NINA, SGP, MaxIm и т.д.).
- Сохранить гибкость управления камерой через Python (единое ядро управления + API для UI).
- Упростить сопровождение и диагностику (логирование, БД, автотесты, UI-панель).

### 2.3 KPI/критерии успеха
- Успешное прохождение Conform/ConformU на целевом наборе функций.
- Стабильные серийные экспозиции без зависаний/утечек.
- Повторяемый процесс развертывания и обновления через миграции.

## 3. Область решения
### Релизы
- **R1 (первый релиз):** запуск без обязательной зависимости от PostgreSQL. Хранение настроек и операционных логов возможно локально (файл/SQLite), PostgreSQL поддерживается как опция.
- **R1.1:** включение PostgreSQL как штатного persistent storage для настроек, профилей и операционного журнала.

### Входит в реализацию
- C# ASCOM Local Server (Camera interface).
- Python camera-service с адаптером GreatEyes SDK.
- Локальное хранилище настроек/логов для R1 и PostgreSQL-режим для R1.1.
- Web UI для операторской проверки и технической диагностики.
- Автотесты на слоях: unit, integration, e2e.

### Не входит (этап 1)
- Удаленное распределенное управление несколькими обсерваториями.
- Полноценный планировщик наблюдений.
- Альпака-мост как основной путь (может быть этапом 2).

## 4. Архитектура решения
## 4.1 Логическая схема
- **ASCOM Local Server (C#)**:
  - регистрируется как COM LocalServer,
  - реализует `ICameraV3`,
  - проксирует вызовы в Python API.
- **Python camera-service**:
  - основной доменный слой работы с камерой,
  - управление жизненным циклом экспозиции,
  - нормализация статусов/ошибок,
  - интерфейс к БД и к SDK.
- **GreatEyes SDK/DLL Adapter**:
  - низкоуровневый вызов native SDK (`ctypes`/`cffi`),
  - сериализация доступа к SDK,
  - контроль таймаутов и retry.
- **PostgreSQL**:
  - настройки драйвера и камеры,
  - профили съемки,
  - журнал операций и ошибок.
- **Web UI (React/Vite)**:
  - тестовый интерфейс оператора,
  - ручной запуск сценариев,
  - просмотр статуса, логов, конфигурации.

## 4.2 Физическое развертывание (этап 1)
- Все компоненты на одном Windows-хосте:
  - `GreatEyes SDK/DLL`,
  - `Python service`,
  - `ASCOM Local Server`,
  - `PostgreSQL` (опционально для R1, штатно для R1.1),
  - `UI` (локально в браузере).

## 4.3 Обоснование архитектуры
- COM Local Server дает максимальную совместимость со старым ASCOM ПО.
- Python слой централизует бизнес-логику и работу с SDK.
- БД обеспечивает управляемость настроек, аудит и воспроизводимость.

## 5. Бизнес-процесс (операционный)
## 5.1 Основной сценарий (экспозиция)
1. Оператор/астрософт выбирает ASCOM-драйвер камеры.
2. ASCOM-приложение вызывает `Connect`.
3. Local Server инициирует `POST /camera/connect` в Python service.
4. Python подключается к SDK, валидирует состояние, возвращает `connected`.
5. ASCOM-приложение вызывает `StartExposure`.
6. Local Server отправляет `POST /camera/exposures`.
7. Python стартует экспозицию в фоне и обновляет состояние.
8. ASCOM-приложение циклически спрашивает `ImageReady`/`CameraState`.
9. По готовности Local Server забирает кадр (`GET /camera/images/latest`) и отдает `ImageArray`.
10. При завершении сессии выполняется `Disconnect`.

## 5.2 Альтернативные ветки
- Ошибка SDK при старте: возврат ошибки с кодом и текстом в ASCOM исключение.
- Таймаут экспозиции: перевод в error-state, лог в БД, возможность `AbortExposure`.
- Потеря соединения: автоматическая попытка reconnect (ограниченная), затем controlled fail.

## 5.3 Ограничение по объектным данным наблюдений
- Через стандартный ASCOM поток в текущем сценарии **не передается надежный идентификатор астрономического объекта**.
- Наименование объекта и научные атрибуты FITS формируются на стороне клиентского ПО (например, MaxIm DL) после получения `ImageArray`.
- Поэтому в этом решении backend **не ведет каталог научных кадров и имен объектов**; хранится только операционная телеметрия и технические метаданные.

## 6. Детализация компонентов
## 6.1 ASCOM Local Server (C#)
### Ответственность
- Реализовать стандартный контракт `ICameraV3`.
- Преобразовывать ASCOM-вызовы в HTTP/gRPC API Python-сервиса.
- Маппить ошибки в ASCOM-исключения (`DriverException`, `NotConnectedException`, etc.).

### Обязательные методы (этап 1)
- `Connected` get/set
- `StartExposure(duration, light)`
- `StopExposure()`, `AbortExposure()`
- `CameraState`, `ImageReady`, `ImageArray`, `LastExposureDuration`, `LastExposureStartTime`
- `BinX/BinY`, `NumX/NumY`, `StartX/StartY`
- `CoolerOn`, `SetCCDTemperature`, `CCDTemperature`
- `CameraXSize`, `CameraYSize`
- `SensorName` (как минимум фиксированное валидное значение из конфигурации/SDK)
- `HasShutter` (корректно выставлен в соответствии с моделью)

### Рекомендуемые методы (если поддержаны SDK, этап 1/1.1)
- `CoolerPower` (для контроля режима прогрева/warm-up)
- `ElectronsPerADU`
- `FullWellCapacity`
- `SensorType`

### Нефункциональные требования
- Максимальное время ответа на status-вызовы: до 200 мс (среднее, локально).
- Без UI-блокировок в runtime (Setup UI только в `SetupDialog`).
- Подробный trace log с correlation-id.

## 6.2 Python camera-service
### Ответственность
- Единый источник состояния камеры.
- Управление сессией подключения, экспозициями и кадрами.
- Валидация входных параметров.
- Доступ к хранилищу (локальному или PostgreSQL) и аудит.

### Предлагаемый стек
- `Python 3.11+`
- `FastAPI` + `uvicorn`
- `SQLAlchemy` + `Alembic`
- `psycopg` (или `asyncpg`)
- `pydantic` модели контрактов

### Внутренние модули
- `api` (REST endpoints)
- `domain` (state machine, use-cases)
- `sdk_adapter` (GreatEyes DLL calls)
- `repository` (storage abstraction: local/pgsql)
- `services` (settings, exposure orchestration, telemetry)

### Режим запуска Python camera-service
- Сервис запускается как отдельный длительно живущий процесс на Windows.
- Целевая версия Python для R1: `3.11`.
- На этапе эксплуатации допускается переход к упаковке в standalone executable (без отдельной ручной установки Python), но это не блокирует R1.

## 6.3 GreatEyes SDK/DLL Adapter
### Ответственность
- Изолировать вызовы native SDK.
- Зафиксировать ABI (типы, calling convention, структура ошибок).
- Обеспечить потокобезопасность через command queue / mutex.

### Требования
- Все вызовы SDK только через один контролируемый execution context.
- Явные timeout/retry политики.
- Нормализация статусов SDK в внутренние коды сервиса.

## 6.4 PostgreSQL
### Задача хранения (этап 1.1)
- Системные настройки драйвера.
- Профили камеры/экспозиций.
- История операций и ошибок.
- Журнал сессий подключения.
- Без хранения научных каталогов объектов наблюдений и без хранения самих FITS кадров.

### Базовый scope таблиц
- `app_settings`
- `camera_profiles`
- `camera_session`
- `exposure_job`
- `exposure_image_meta`
- `event_log`

## 6.5 UI (MVP для проверки)
### Назначение
- Техпанель для верификации работоспособности.
- Не заменяет ASCOM-клиенты, а проверяет backend.

### Экраны
- `Connection`: connect/disconnect, состояние SDK.
- `Exposure`: параметры, start/stop/abort, прогресс.
- `Image`: метаданные последнего кадра, предпросмотр (опционально downsample).
- `Cooling`: текущая/целевая температура, cooler on/off.
- `Settings`: профили, сохранение в БД.
- `Logs`: события/ошибки с фильтрацией.

### Отдельный сценарий warm-up
- В UI добавляется операция "Warm-up", которая не делает резкий `CoolerOff`.
- Алгоритм warm-up:
  1. Если SDK поддерживает `CoolerPower`, поэтапно снижать мощность (например, шагами 10%).
  2. Параллельно повышать target temperature ступенями (например, по 5C до безопасной зоны).
  3. После достижения порога (например, выше 0C или заданного значения) выполнять `CoolerOff`.
- Все шаги логируются как отдельные операционные события.

## 7. Data Flow (сквозные потоки)
## 7.1 Connect flow
- ASCOM App -> C# `Connected=true` -> Python `POST /camera/connect` -> SDK `ConnectCamera` -> DB `camera_session` + `event_log`.

## 7.2 Exposure flow
- ASCOM App -> C# `StartExposure` -> Python `POST /camera/exposures` -> SDK `StartMeasurement`.
- Polling: C# `ImageReady` -> Python `GET /camera/exposures/{id}/status` -> SDK `DllIsBusy`.
- Completion: Python `GetMeasurementData` -> cache + `exposure_image_meta`.
- Read image: C# `ImageArray` -> Python `GET /camera/images/latest` -> ASCOM array.

## 7.3 Cooling flow
- C# `SetCCDTemperature` / `CoolerOn` -> Python API -> SDK temperature functions -> DB log.
- Для завершения сессии рекомендуется `Warm-up flow` вместо мгновенного `CoolerOff`.

### 7.3.1 Бизнес-правило для `target_temp_c` в SDK level-mode
Проблема: в части моделей/режимов GreatEyes SDK (`TemperatureControl_Setup` / level-mode) не возвращает надежный абсолютный диапазон `min..max` в градусах C, а работает через дискретные уровни охлаждения `1..N`.

Принятое правило для R1/R1.1:
1. Если SDK дает валидный абсолютный диапазон (`TemperatureControl_Init` с ненулевыми `min/max`) -> использовать абсолютный API `TemperatureControl_SetTemperature(target_temp_c)`.
2. Если SDK в level-mode (абсолютный диапазон недоступен) -> использовать `TemperatureControl_SetTemperatureLevel(level)` по детерминированному маппингу.
3. Маппинг выполняется линейно в "виртуальном" бизнес-диапазоне:
   - `-80 C` соответствует `level = N` (максимальное охлаждение),
   - `+20 C` соответствует `level = 1` (минимальное охлаждение),
   - значения вне диапазона `[-80; +20]` жестко clamp-ятся.

Формула для level-mode:
- `target_clamped = clamp(target_temp_c, -80, +20)`
- `cold_ratio = (20 - target_clamped) / 100`
- `level = round(1 + cold_ratio * (N - 1))`
- итог: `level = clamp(level, 1, N)`

Пример (при `N=10`):
- `target_temp_c = -80` -> `level=10`
- `target_temp_c = -50` -> `level=7`
- `target_temp_c = -20` -> `level=5`
- `target_temp_c = 0` -> `level=3`
- `target_temp_c = +20` -> `level=1`

Цель правила:
- единообразное поведение для ASCOM-клиентов при отсутствии абсолютного temperature API,
- предсказуемость и повторяемость между запусками,
- совместимость с warm-up сценарием (ступенчатое снижение охлаждения).

## 8. Контракты (кратко)
Подробно в отдельном документе `02_Контракты_API_и_методы.md`.

Ключевые endpoints:
- `POST /camera/connect`
- `POST /camera/disconnect`
- `GET /camera/state`
- `POST /camera/exposures`
- `POST /camera/exposures/{id}/abort`
- `GET /camera/exposures/{id}/status`
- `GET /camera/images/latest`
- `POST /camera/cooling`
- `GET /settings`, `PUT /settings`

## 9. Подключение к БД и миграции (кратко)
Подробно в `03_PostgreSQL_схема_и_миграции.md`.

Конфиг подключения (placeholder):
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_SSLMODE`.

Миграции:
- `Alembic` для Python-сервиса.
- SQL-скрипты миграций хранятся в репозитории и проходят code review.

## 10. Нефункциональные требования
- Надежность: корректное восстановление после сбоев SDK.
- Наблюдаемость: структурные логи + event log в storage (R1 local, R1.1 PostgreSQL).
- Производительность: корректная обработка больших массивов кадра (без лишних копий).
- Безопасность: доступ к API только localhost (этап 1), секреты БД через env vars.

## 11. Риски и меры
- **SDK потоконебезопасен** -> single-thread executor и очередь команд.
- **Несоответствие форматов изображения** -> единая спецификация pixel format и orientation.
- **Зависимость от локальных DLL** -> healthcheck и проверка версии SDK при старте.
- **Расхождение состояний ASCOM и backend** -> централизованная state machine и TTL для статусов.

## 12. Этапы реализации
1. Каркас Python service + local storage (без обязательной БД).
2. SDK adapter и базовые методы connect/exposure/cooling.
3. ASCOM Local Server адаптер к API и обязательные свойства `ICameraV3`.
4. UI MVP (включая warm-up сценарий).
5. Полный набор автотестов (unit/integration/e2e).
6. Интеграционное тестирование с железом + Conform.
7. Подключение PostgreSQL и миграций как этап R1.1.

## 13. Артефакты поставки
- Исходный код C# Local Server.
- Исходный код Python service + Alembic migrations.
- UI проект.
- Документация и test checklist.
- Инструкции запуска и smoke-check.

## 14. Ссылка на подход Local Server
- https://td0g.ca/2019/01/10/writing-an-ascom-local-server-driver/
