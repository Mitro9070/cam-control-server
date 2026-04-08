# Этап 2: GreatEyes SDK Adapter (прогресс)

## Реализовано
- Добавлен SDK adapter слой в Python service:
  - `MockGreatEyesSdkAdapter`
  - `NativeGreatEyesSdkAdapter` (ctypes + ABI сигнатуры)
- Реализованы операции:
  - `connect`
  - `disconnect`
  - `capabilities`
- Добавлена нормализация ошибок SDK:
  - `SdkErrorCode`
  - mapping status codes -> messages

## Подключено в API
- `POST /api/v1/camera/connect`
- `POST /api/v1/camera/disconnect`
- `GET /api/v1/camera/capabilities`
- `GET /api/v1/camera/state` теперь отражает runtime состояние.

## Тесты
- Обновлены и пройдены тесты API:
  - `3 passed`

## Примечание
- По умолчанию `SDK_MODE=mock`.
- Для перехода на реальную DLL нужен путь в `SDK_DLL_PATH` и `SDK_MODE=native`.
