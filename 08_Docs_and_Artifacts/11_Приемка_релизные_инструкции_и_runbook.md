# Приемка: релизные инструкции и runbook

## 1) Область приемки (R1)
- ASCOM Local Server (`C#`) для `ICameraV3` базового профиля.
- Python camera-service (API + storage + warm-up).
- UI панель проверки (`/ui`).
- Автотесты: Python unit/integration/migrations, C# unit, UI smoke e2e.

## 2) Релизный пакет (что передаем)
- C# проект: `Project_R1/01_ASCOM_Local_Server`
- Python service: `Project_R1/02_Python_Camera_Service`
- UI: `Project_R1/05_UI/web`
- Тестовый контур: `Project_R1/06_Testing`
- Документация/артефакты: `Project_R1/08_Docs_and_Artifacts`

## 3) Runbook: запуск перед приемкой

### 3.1 Backend
- Перейти в `Project_R1/02_Python_Camera_Service`.
- Убедиться, что `.env` настроен.
- Запустить:
  - `python -m uvicorn app.main:app --host 127.0.0.1 --port 3037`
- Проверить:
  - `http://127.0.0.1:3037/api/v1/health`
  - `http://127.0.0.1:3037/ui/`

### 3.2 C# драйвер
- Убедиться, что сборка актуальна:
  - `MSBuild ... ASCOM.ProjectR1.LocalServer.sln /t:Rebuild`
- Убедиться, что COM registration выполнена (если новая машина):
  - `RegAsm ... ASCOM.ProjectR1.Camera.dll /codebase`
- При необходимости переопределить URL backend для драйвера:
  - env var `PROJECT_R1_API_BASE_URL` (по умолчанию `http://127.0.0.1:3037/api/v1`).
- Проверить наличие драйвера в ASCOM profile/Chooser.

### 3.3 Автотесты
- Python:
  - `cd Project_R1/02_Python_Camera_Service`
  - `python -m pytest -q`
- C# unit:
  - `dotnet test Project_R1/06_Testing/ASCOM.ProjectR1.Camera.Tests/ASCOM.ProjectR1.Camera.Tests.csproj`
- UI smoke:
  - `cd Project_R1/06_Testing`
  - `npm run test:ui-smoke`

### 3.4 Conform/ConformU
- Выполнить по документу:
  - `10_Conform_ConformU_тест_кейсы_и_runnable_checklist.md`

## 4) Минимальные критерии приемки
- Все автотесты зеленые.
- UI smoke проходит.
- Драйвер виден в ASCOM Chooser.
- Критичные Conform/ConformU кейсы пройдены.
- Нет критичных ошибок High.

## 5) Риски перед финальной приемкой
- Native SDK контур все еще требует полного стендового прогона на железе (техдолг).
- Финальный wire-format `ImageArray` между Python/C# может потребовать уточнений на реальных клиентах.

## 6) План действий в день приемки
- T-60 мин: старт сервисов и smoke.
- T-45 мин: прогон автотестов.
- T-30 мин: Conform/ConformU.
- T-15 мин: фиксация протокола (passed/failed/blockers).
- T-0: решение Go/No-Go.
