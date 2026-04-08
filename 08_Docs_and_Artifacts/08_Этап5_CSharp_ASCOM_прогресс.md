# Этап 5: C# ASCOM Local Server (прогресс)

## Реализовано
- Создан каркас C# решения:
  - `Project_R1/01_ASCOM_Local_Server/ASCOM.ProjectR1.LocalServer.sln`
  - `src/ASCOM.ProjectR1.Camera/ASCOM.ProjectR1.Camera.csproj`
- Добавлен драйвер `Camera` с реализацией `ICameraV3` (R1 профиль).
- Добавлен HTTP proxy-клиент к Python API:
  - `PythonApiClient.cs`
- Добавлены COM registration hooks:
  - `[ComRegisterFunction]`
  - `[ComUnregisterFunction]`
- Реализованы ключевые блоки:
  - connect/disconnect
  - state/capabilities
  - exposure start/status/stop/abort
  - image retrieval (`ImageArray`)
  - ROI/binning forwarding
  - cooling/temperature/setpoint/cooler power
  - properties `CameraXSize`, `CameraYSize`, `SensorName`, `HasShutter`

## Текущий статус окружения
- `dotnet` и `MSBuild` доступны в shell.
- `ASCOM Platform 7` установлена, сборки `ASCOM.*` доступны в системе.
- CLI-сборка решения `ASCOM.ProjectR1.LocalServer.sln` успешна.

## Завершение этапа 5
- COM registration драйвера выполнена через `RegAsm`.
- В реестре присутствуют:
  - `HKEY_CLASSES_ROOT\ASCOM.ProjectR1.Camera`
  - `HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\ASCOM\Camera Drivers\ASCOM.ProjectR1.Camera`
- Сборка и регистрация подтверждены для перехода к этапу 6 (UI).
