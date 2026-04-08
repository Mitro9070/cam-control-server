# Conform/ConformU: тест-кейсы и runnable checklist

## 1) Цель
- Подтвердить соответствие драйвера `ASCOM.ProjectR1.Camera` интерфейсу `ICameraV3`.
- Зафиксировать блокирующие и неблокирующие замечания перед приемкой.

## 2) Предусловия
- Установлен `ASCOM Platform 7.x`.
- Драйвер зарегистрирован и виден в ASCOM профиле:
  - `ASCOM.ProjectR1.Camera`.
- Запущен backend:
  - `python -m uvicorn app.main:app --host 127.0.0.1 --port 3037`
- Доступен UI:
  - `http://127.0.0.1:3037/ui/`
- Режим SDK для приемочных тестов:
  - `SDK_MODE=mock` (для сухого прогона),
  - затем `SDK_MODE=native` (на стенде с железом, отдельный прогон).

## 3) Набор тест-кейсов для Conform/ConformU

### CFM-CAM-001: Регистрация и выбор драйвера
- **Шаги:** открыть Conform/ConformU -> Camera -> выбрать `ASCOM.ProjectR1.Camera`.
- **Ожидание:** драйвер успешно выбирается, без ошибки регистрации COM.
- **Критичность:** High (блокер релиза).

### CFM-CAM-002: Connected true/false
- **Шаги:** выполнить connect/disconnect через Conform.
- **Ожидание:** `Connected` меняется корректно, нет зависаний.
- **Критичность:** High.

### CFM-CAM-003: Базовые свойства камеры
- **Проверяем:** `CameraXSize`, `CameraYSize`, `SensorName`, `HasShutter`.
- **Ожидание:** значения валидны и не пустые; размеры > 0.
- **Критичность:** High.

### CFM-CAM-004: Экспозиция (StartExposure/ImageReady/ImageArray)
- **Шаги:** старт экспозиции 1s -> poll `ImageReady` -> чтение `ImageArray`.
- **Ожидание:** `ImageReady=true`, `ImageArray` читается без исключений.
- **Критичность:** High.

### CFM-CAM-005: StopExposure/AbortExposure
- **Шаги:** старт длинной экспозиции -> `StopExposure`; затем отдельный прогон с `AbortExposure`.
- **Ожидание:** корректное завершение без deadlock/timeout.
- **Критичность:** High.

### CFM-CAM-006: Температура и cooler
- **Проверяем:** `CoolerOn`, `SetCCDTemperature`, `CCDTemperature`, `CoolerPower`.
- **Ожидание:** команды выполняются, значения в допустимых диапазонах.
- **Критичность:** High.

### CFM-CAM-007: ROI/Binning
- **Проверяем:** `StartX/StartY`, `NumX/NumY`, `BinX/BinY`.
- **Ожидание:** параметры применяются без ошибок, не выходят за размер сенсора.
- **Критичность:** Medium.

### CFM-CAM-008: Поведение не реализованных методов
- **Проверяем:** `PulseGuide`, `Gain`, и др. NotImplemented элементы.
- **Ожидание:** корректные ASCOM exceptions (`MethodNotImplementedException`/`PropertyNotImplementedException`), без падения процесса.
- **Критичность:** Medium.

### CFM-CAM-009: Стресс connect/disconnect
- **Шаги:** 20 циклов connect/disconnect.
- **Ожидание:** нет утечек, зависаний, критических ошибок.
- **Критичность:** High.

### CFM-CAM-010: Логирование и трассировка
- **Проверяем:** события в `event_log`/local events.
- **Ожидание:** есть записи для connect/exposure/cooling/warm-up.
- **Критичность:** Medium.

## 4) Runnable checklist (оператор)

### Шаг A: Подготовка среды
- [ ] Убедиться, что backend запущен на `127.0.0.1:3037`.
- [ ] Проверить `GET /api/v1/health` -> `status=ok`.
- [ ] Проверить UI `http://127.0.0.1:3037/ui/`.

### Шаг B: Быстрый smoke перед Conform
- [ ] `Connect` в UI выполняется.
- [ ] Экспозиция 1s в UI завершается (`ImageReady`).
- [ ] `Latest image` читается.
- [ ] `Cooling` и `Warm-up` отрабатывают без ошибок.

### Шаг C: Прогон Conform/ConformU
- [ ] CFM-CAM-001
- [ ] CFM-CAM-002
- [ ] CFM-CAM-003
- [ ] CFM-CAM-004
- [ ] CFM-CAM-005
- [ ] CFM-CAM-006
- [ ] CFM-CAM-007
- [ ] CFM-CAM-008
- [ ] CFM-CAM-009
- [ ] CFM-CAM-010

### Шаг D: Критерии Go/No-Go
- [ ] Нет блокирующих ошибок по High-кейсам.
- [ ] Нет падений драйвера/процесса backend.
- [ ] Все критичные кейсы документированы в протоколе.

## 5) Шаблон протокола результата
- Дата/время прогона:
- Версия драйвера/сборки:
- Режим SDK (`mock/native`):
- Версия Conform/ConformU:
- Итог:
  - Passed:
  - Failed:
  - Blockers:
  - Комментарии:
