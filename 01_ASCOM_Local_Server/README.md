# 01_ASCOM_Local_Server

Зона реализации ASCOM Local Server (C#):
- проект драйвера,
- реализация `ICameraV3`,
- registration,
- интеграция с Python API.

## Текущее состояние
- Добавлен каркас C# проекта: `ASCOM.ProjectR1.Camera`.
- Реализован первичный proxy-драйвер `ICameraV3` с вызовами Python API.
- Добавлены COM register/unregister hooks через ASCOM Profile.

## Файлы
- `ASCOM.ProjectR1.LocalServer.sln`
- `src/ASCOM.ProjectR1.Camera/ASCOM.ProjectR1.Camera.csproj`
- `src/ASCOM.ProjectR1.Camera/CameraDriver.cs`
- `src/ASCOM.ProjectR1.Camera/PythonApiClient.cs`
