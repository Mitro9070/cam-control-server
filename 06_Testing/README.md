# 06_Testing

Тестовый контур:
- unit tests,
- integration tests,
- e2e smoke tests,
- Conform/ConformU сценарии.

## UI smoke (Playwright)

Предусловие: запущен backend с UI на `http://127.0.0.1:3037`.

Команды:
- `npm install`
- `npx playwright install chromium`
- `npm run test:ui-smoke`

## C# unit tests (ASCOM layer)

Путь проекта:
- `ASCOM.ProjectR1.Camera.Tests/ASCOM.ProjectR1.Camera.Tests.csproj`

Запуск:
- `dotnet test ASCOM.ProjectR1.Camera.Tests/ASCOM.ProjectR1.Camera.Tests.csproj`

## Python integration + migration tests

Путь:
- `../02_Python_Camera_Service/tests`

Запуск:
- `cd ../02_Python_Camera_Service`
- `python -m pytest -q`
