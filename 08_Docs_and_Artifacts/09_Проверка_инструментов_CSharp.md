# Проверка инструментов C# (после установки)

## Что подтверждено
- `dotnet` доступен: `9.0.311`.
- `MSBuild` установлен и доступен по пути:
  - `C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\MSBuild\Current\Bin\MSBuild.exe`
- `ASCOM Platform 7` установлена, каталог `C:\Program Files (x86)\Common Files\ASCOM` присутствует.
- C# solution успешно собирается через `MSBuild`.

## Что выявлено и исправлено
- Ранее отсутствующие `ASCOM.*` сборки стали доступны после установки платформы.
- Для устранения конфликтов версий в `ASCOM.ProjectR1.Camera.csproj` зафиксированы `HintPath` на `Platform` (без `Platform55`).
- Исправлена ошибка компиляции в `CameraDriver.cs`: `ActionNotImplementedException` заменен на `MethodNotImplementedException`.
- Сборка `ASCOM.ProjectR1.LocalServer.sln` проходит успешно (`Warnings: 0`, `Errors: 0`).

## Статус регистрации
- COM registration драйвера выполнена в elevated PowerShell через `RegAsm`.
- Зарегистрирован `ProgID`:
  - `HKEY_CLASSES_ROOT\ASCOM.ProjectR1.Camera`
- Драйвер присутствует в ASCOM camera profile:
  - `HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\ASCOM\Camera Drivers\ASCOM.ProjectR1.Camera`

## Следующий шаг
- Этап 5 закрыт.
- Переход к этапу 6: UI MVP + e2e smoke сценарии.
