# План доработок ASCOM (версия 2.2)

Дата: 2026-03-27  
Контур: `ASCOM.ProjectR1.Camera` → Python `camera-service` → GreatEyes SDK

Использование: по мере выполнения работ отмечайте пункты как `[x]`.

**Статус реализации (2026-03-27):** кодовая часть v2.2 внесена; ручная проверка в MaxIm DL остаётся на стороне площадки.

---

## P0. Охлаждение и синхронизация с сервером

- [x] `SetCCDTemperature` (getter) отражает актуальный `target_temp_c` с `GET /camera/cooling/status`, а не только локальный кэш.
- [x] После `Connected=true` синхронизировать состояние охлаждения с сервером (`cooler_on`, целевая температура).
- [x] При `SetCCDTemperature` (setter) подтверждать значение из ответа `PUT /camera/cooling/target`.
- [x] `CoolerOn` (getter) отражает фактическое состояние с сервера.
- [x] При включении кулера не форсировать фиксированный процент мощности в запросе (передать управление алгоритму сервиса).

**Файлы:**  
[01_ASCOM_Local_Server/src/ASCOM.ProjectR1.Camera/CameraDriver.cs](c:/Project/Project_R1/01_ASCOM_Local_Server/src/ASCOM.ProjectR1.Camera/CameraDriver.cs)

---

## P1. Setup / Properties (ASCOM)

- [x] Реализовать `SetupDialog()`: модальное окно с основными параметрами и сохранением в ASCOM Profile.
- [x] В диалоге: скорость считывания (фиксированный список), режим gain (человекочитаемые подписи), опционально активация профиля камеры по `profile_id`.
- [x] Применение настроек через `PUT /api/v1/settings` (и при необходимости `POST /api/v1/camera/profiles/{id}/activate`).

**Файлы:**  
[01_ASCOM_Local_Server/src/ASCOM.ProjectR1.Camera/CameraSetupForm.cs](c:/Project/Project_R1/01_ASCOM_Local_Server/src/ASCOM.ProjectR1.Camera/CameraSetupForm.cs)  
[01_ASCOM_Local_Server/src/ASCOM.ProjectR1.Camera/ASCOM.ProjectR1.Camera.csproj](c:/Project/Project_R1/01_ASCOM_Local_Server/src/ASCOM.ProjectR1.Camera/ASCOM.ProjectR1.Camera.csproj)

---

## P1. Gain и Readout в ASCOM (`ICameraV3`)

- [x] `ReadoutModes` / `ReadoutMode`: дискретные режимы, согласованные с `READOUT_SPEED_OPTIONS` в Python.
- [x] `Gain` / `GainMin` / `GainMax` / `Gains`: режимы `0`/`1` с подписями High capacity / Low noise; чтение/запись через `GET/PUT /settings`.
- [x] При изменении readout/gain при подключенной камере применять параметры к SDK без обязательного reconnect.

**Файлы:**  
[01_ASCOM_Local_Server/src/ASCOM.ProjectR1.Camera/CameraDriver.cs](c:/Project/Project_R1/01_ASCOM_Local_Server/src/ASCOM.ProjectR1.Camera/CameraDriver.cs)  
[02_Python_Camera_Service/app/sdk_adapter.py](c:/Project/Project_R1/02_Python_Camera_Service/app/sdk_adapter.py)  
[02_Python_Camera_Service/app/camera_runtime.py](c:/Project/Project_R1/02_Python_Camera_Service/app/camera_runtime.py)  
[02_Python_Camera_Service/app/api/routes.py](c:/Project/Project_R1/02_Python_Camera_Service/app/api/routes.py)

---

## P2. WarmUp и расширяемость ASCOM

- [x] Зарегистрировать vendor action (например `ProjectR1:WarmUp`) в `SupportedActions` / `Action()`.
- [x] Вызов `POST /camera/cooling/warmup` с параметрами по умолчанию или из строки параметров.

**Примечание:** параметры warmup пока фиксированы в коде (`target_temp_c=0`, `temp_step_c=5`, `power_step_percent=10`, `step_interval_sec=30`); разбор `actionParameters` можно добавить отдельно.

**Файлы:**  
[01_ASCOM_Local_Server/src/ASCOM.ProjectR1.Camera/CameraDriver.cs](c:/Project/Project_R1/01_ASCOM_Local_Server/src/ASCOM.ProjectR1.Camera/CameraDriver.cs)

---

## P2. Тесты и приёмка

- [x] Прогон `dotnet test` для решения ASCOM.
- [x] Прогон `pytest` для Python-сервиса.
- [ ] Ручная проверка в MaxIm DL: setpoint = «цель охлаждения» на сервере; смена Readout/Gain из Properties.

**Файлы:**  
[01_ASCOM_Local_Server/tests/ASCOM.ProjectR1.Camera.Tests](c:/Project/Project_R1/01_ASCOM_Local_Server/tests/ASCOM.ProjectR1.Camera.Tests)  
[02_Python_Camera_Service/tests/test_api.py](c:/Project/Project_R1/02_Python_Camera_Service/tests/test_api.py)

---

## Критерии готовности v2.2

- [x] Температура, заданная в клиенте ASCOM, совпадает с целевой на сервере (в т.ч. после переподключения). — *реализовано в драйвере; подтверждение в MaxIm — вручную.*
- [x] Оператор может открыть Properties и задать скорость считывания и gain до/после connect (с применением к SDK при connect). — *Properties + `PUT /settings` + `apply_sdk_imaging_settings` при connect.*
- [x] Доступен программный вызов warmup через `Action` (для сценариев без отдельной кнопки в стандарте). — *action `ProjectR1:WarmUp`.*
