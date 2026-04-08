# Инженерный протокол интеграции GreatEyes SDK

## Цель
Получить стабильное подключение реальной сетевой камеры (`192.168.31.234`) из `Project_R1` в `SDK_MODE=native`.

## Зафиксированное состояние
- `greateyesVision` на этом ПК умеет подключаться к камере по `192.168.31.234:12345`.
- `Project_R1` после деплоя запускается штатно (`health/ui/db` OK).
- В native-режиме `ConnectCamera` из Python возвращает `status=1` (`no camera detected`) при свободной камере.
- При некоторых экспериментальных вызовах `ConnectTo*` получали `status=10` (`camera busy`) и access violation при неверных сигнатурах.

## Важные гипотезы
1. Для сетевого режима нужен обязательный bootstrap-порядок вызовов SDK перед `ConnectCamera`.
2. Часть функций имеет отличающиеся сигнатуры/конвенции вызова в конкретной сборке `greateyes.dll`.
3. `greateyesVision` использует актуальный профиль из `C:\ProgramData\greateyes\2\greateyes.ini` (`Camera0_Interface=3`, `Camera0_Address=192.168.31.234`).

## Что уже внедрено в код
- В `app/config.py` добавлены параметры:
  - `sdk_camera_address`
  - `sdk_camera_interface`
  - `sdk_camera_port`
- В `app/sdk_adapter.py` добавлена автосинхронизация сетевых параметров в `greateyes.ini` перед `ConnectCamera`.
- В `.env` выставлены:
  - `SDK_CAMERA_ADDRESS=192.168.31.234`
  - `SDK_CAMERA_INTERFACE=3`
  - `SDK_CAMERA_PORT=12345`

## Протокол отладки (пошагово)

### Шаг 1. Контроль внешней занятости
- Убедиться, что `greateyesVision` закрыт перед тестом.
- Проверить отсутствие активных соединений от сторонних процессов к `192.168.31.234:12345`.

### Шаг 2. Базовый native smoke
- `POST /api/v1/camera/connect`
- `GET /api/v1/camera/state`
- `GET /api/v1/logs/events?limit=20`
- Фиксировать `error_code`, `message`, `status` SDK.

### Шаг 3. Низкоуровневый SDK-probe (вне сервиса)
- Прогонять отдельным процессом Python, чтобы не рисковать падением `uvicorn`.
- Сценарий:
  - загрузить DLL,
  - выполнить `ConnectCamera` для индексов `0..3`,
  - собрать статусы и модель.

### Шаг 4. Эксперименты с сетевыми API SDK
- Выполнять только через отдельный probe-скрипт.
- Кандидаты:
  - `SetupCameraInterface`
  - `SetConnectionType`
  - `ConnectToCameraServer`
  - `ConnectToSingleCameraServer`
- Для каждого варианта фиксировать:
  - сигнатуру, с которой вызвали,
  - return value,
  - SDK status от последующего `ConnectCamera`.

### Фактический прогон на этом ПК (2026-03-07)
- Выполнен изолированный перебор сценариев:
  - `tools/probe_greateyes_network_handshake.py`
- Результат:
  - рабочей последовательности со статусом `ConnectCamera=0` не найдено;
  - часть комбинаций дает `status=10 (camera busy)` и access violation (признак неверной сигнатуры для конкретного вызова);
  - стабильный baseline без спорных вызовов остается `status=1 (no camera detected)`.
- Вывод:
  - без официальных прототипов вендора сигнатуры `ConnectTo*` / `SetConnectionType` / `CheckCamera*` нельзя считать подтвержденными.

### Шаг 5. Выбор рабочей последовательности
- Критерий успеха:
  - `ConnectCamera` -> `status=0`, `connected=True`.
- После успеха:
  - `capabilities`,
  - `roi`,
  - `exposure`,
  - `cooling`.

## Безопасные правила
- Не вызывать неизвестные `ConnectTo*` сигнатуры внутри API сервиса напрямую.
- Все рискованные вызовы сначала в изолированном probe-процессе.
- После каждого неуспешного/сомнительного вызова перезапускать SDK-контур (или сервис), чтобы не переносить "грязное" состояние.

## Артефакты, которые нужно запросить у вендора
- Официальный `SDK header`/документация по `greateyes.dll` для network mode.
- Точные сигнатуры и calling convention функций `ConnectTo*`, `Setup*`, `SetConnectionType`.
- Рекомендованный порядок вызовов для IP-камеры.
