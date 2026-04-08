# 05_UI

UI для проверки и диагностики:
- Connection,
- Exposure,
- Cooling (включая warm-up),
- Settings,
- Logs.

## Запуск

1. Поднять Python camera-service.
2. Открыть в браузере:
   - `http://127.0.0.1:3037/ui/`

UI отдается самим FastAPI сервисом, поэтому работает без CORS-настроек.
