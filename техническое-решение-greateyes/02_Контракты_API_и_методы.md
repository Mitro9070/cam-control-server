# Контракты API и методы

## 1. Общие правила API
- Базовый URL (локально): `http://127.0.0.1:3037/api/v1`
- Формат: `application/json`
- Корреляция: заголовок `X-Correlation-Id` (генерируется клиентом или сервером)
- Ошибки: единый формат
- Ограничение: API не принимает и не хранит "object name" наблюдения как обязательный доменный атрибут (это зона клиентского астрософта и FITS-пайплайна).

```json
{
  "error_code": "SDK_TIMEOUT",
  "message": "GetMeasurementData timed out",
  "details": {},
  "correlation_id": "..."
}
```

## 2. Маппинг ASCOM -> Python API
| ASCOM `ICameraV3` | Python endpoint | Примечание |
|---|---|---|
| `Connected=true` | `POST /camera/connect` | Подключение к SDK |
| `Connected=false` | `POST /camera/disconnect` | Закрытие сессии |
| `CameraState` | `GET /camera/state` | Возвращает enum состояния |
| `StartExposure(d, l)` | `POST /camera/exposures` | Асинхронный старт |
| `AbortExposure()` | `POST /camera/exposures/{id}/abort` | Принудительная отмена |
| `StopExposure()` | `POST /camera/exposures/{id}/stop` | Корректная остановка |
| `ImageReady` | `GET /camera/exposures/{id}/status` | `image_ready=true/false` |
| `ImageArray` | `GET /camera/images/latest/raw` | Бинарный `uint16` кадр для ASCOM/MaxIm DL |
| `BinX/BinY/NumX/NumY/StartX/StartY` | `PUT /camera/config/roi-binning` | ROI/Subframe + binning |
| `CoolerOn` | `PUT /camera/cooling/power` | on/off |
| `SetCCDTemperature` | `PUT /camera/cooling/target` | target C |
| `CCDTemperature` | `GET /camera/cooling/status` | текущая температура |
| `CameraXSize/CameraYSize` | `GET /camera/capabilities` | размеры сенсора |
| `SensorName` | `GET /camera/capabilities` | имя сенсора |
| `HasShutter` | `GET /camera/capabilities` | наличие механического затвора |
| `CoolerPower` | `GET /camera/cooling/status` | если поддержано SDK |

## 3. Контракты endpoint'ов
## 3.1 Подключение
### POST `/camera/connect`
Request:
```json
{
  "camera_index": 0,
  "readout_speed": 500,
  "gain_mode": "1"
}
```
Response:
```json
{
  "connected": true,
  "camera_model_id": 12345,
  "camera_model_name": "GreatEyes ELSE 2K"
}
```

### POST `/camera/disconnect`
Response:
```json
{
  "connected": false
}
```

## 3.2 Состояние камеры
### GET `/camera/state`
Response:
```json
{
  "connected": true,
  "camera_state": "idle",
  "image_ready": false,
  "active_exposure_id": null
}
```

`camera_state`:
- `idle`
- `exposing`
- `reading`
- `error`
- `disconnected`

## 3.2.1 Возможности/паспорт камеры
### GET `/camera/capabilities`
Response:
```json
{
  "camera_x_size": 2048,
  "camera_y_size": 2052,
  "sensor_name": "GreatEyes ELSE 2K",
  "has_shutter": true,
  "sensor_type": "Monochrome",
  "electrons_per_adu": 1.0,
  "full_well_capacity": 100000,
  "supports_cooler_power": true
}
```

## 3.3 Экспозиции
### POST `/camera/exposures`
Request:
```json
{
  "duration_sec": 1.5,
  "light": true,
  "bin_x": 1,
  "bin_y": 1,
  "num_x": 2048,
  "num_y": 2052,
  "start_x": 0,
  "start_y": 0,
  "profile_id": "optional-uuid"
}
```

### ROI/Subframe semantics
- Конфигурация `Subframe` и `Binning` задается отдельно через `PUT /camera/config/roi-binning` до `StartExposure`.
- Геометрия проверяется по формуле:
  - `start_x + num_x * bin_x <= camera_x_size`
  - `start_y + num_y * bin_y <= camera_y_size`
- Для native SDK чтение из DLL по-прежнему выполняется через буфер полного кадра (во избежание `access violation`), после чего ROI/Subframe и binning применяются в runtime перед отдачей `ImageArray`.
- Это обеспечивает совместимость с ASCOM-клиентами, включая MaxIm DL, где `StartX/StartY/NumX/NumY` могут устанавливаться по отдельности.
Response:
```json
{
  "exposure_id": "uuid",
  "started_at": "2026-03-03T14:00:00Z",
  "state": "exposing"
}
```

### GET `/camera/exposures/{exposure_id}/status`
Response:
```json
{
  "exposure_id": "uuid",
  "state": "reading",
  "percent": 90,
  "image_ready": false,
  "error": null
}
```

### POST `/camera/exposures/{exposure_id}/abort`
Response:
```json
{
  "exposure_id": "uuid",
  "state": "aborted"
}
```

### POST `/camera/exposures/{exposure_id}/stop`
Response:
```json
{
  "exposure_id": "uuid",
  "state": "stopped"
}
```

## 3.4 Изображение
### GET `/camera/images/latest`
JSON-формат для UI/отладки (метаданные + `sample_pixels` + `pixel_data_base64`).

### GET `/camera/images/latest/raw`
Финальный wire-format для ASCOM `ImageArray`:
- `Content-Type: application/octet-stream`
- Body: `uint16 little-endian`, размер `width * height * 2`
- Метаданные в headers:
  - `X-Exposure-Id`
  - `X-Width`
  - `X-Height`
  - `X-Pixel-Type`
  - `X-Orientation`
  - `X-Bin-X`
  - `X-Bin-Y`

Response metadata:
```json
{
  "exposure_id": "uuid",
  "width": 2048,
  "height": 2052,
  "pixel_type": "uint16",
  "orientation": "top_left_origin",
  "bin_x": 1,
  "bin_y": 1
}
```

### GET `/camera/images/latest/metadata`
Метаданные последнего кадра без пиксельных данных.

### POST `/camera/images/latest/resize`
Изменение размера (uint16, nearest-neighbor), ответ с `pixel_data_base64`.

### POST `/camera/images/latest/export/fits`
Сохранение последнего кадра в FITS под `02_Python_Camera_Service/exports/`.

Request:
```json
{
  "file_name": "exposure.fits"
}
```

Response:
```json
{
  "file_name": "exposure.fits",
  "file_path": ".../exports/exposure.fits",
  "bytes_written": 12345678,
  "exposure_id": "uuid",
  "width": 2048,
  "height": 2052,
  "fits_bitpix": 32,
  "sensor_bit_depth": 16
}
```

**BITPIX (разрядность FITS):** задаётся настройкой `fits_export_bitpix` в `GET/PUT /settings` (допустимо `16` или `32`). Значение по умолчанию `32` — целые 32 бита big-endian, ADU 0..65535 как у uint16 сенсора; `16` — классический FITS int16 с `BZERO=32768`. Переменная окружения `FITS_EXPORT_BITPIX` задаёт стартовый дефолт до сохранения в БД/local JSON.

## 3.5 Cooling
### PUT `/camera/cooling/power`
Request:
```json
{
  "cooler_on": true,
  "cooler_level": 1
}
```

### PUT `/camera/cooling/target`
Request:
```json
{
  "target_temp_c": -90
}
```

### GET `/camera/cooling/status`
Response:
```json
{
  "cooler_on": true,
  "target_temp_c": -90,
  "ccd_temp_c": -88,
  "backside_temp_c": 25,
  "cooler_power_percent": 62
}
```

### POST `/camera/cooling/warmup`
Назначение: безопасный выход из режима глубокого охлаждения.

Request:
```json
{
  "target_temp_c": 0,
  "temp_step_c": 5,
  "power_step_percent": 10,
  "step_interval_sec": 30
}
```

Response:
```json
{
  "warmup_job_id": "uuid",
  "state": "running"
}
```

### GET `/camera/cooling/warmup/{warmup_job_id}/status`
Response:
```json
{
  "warmup_job_id": "uuid",
  "state": "running",
  "current_temp_c": -15,
  "current_power_percent": 20,
  "next_step_at": "2026-03-04T20:00:00Z"
}
```

Совместимость:
- также поддержан путь `GET /camera/cooling/warmup/{warmup_job_id}`.

## 3.6 Настройки
### GET `/settings`
Response (фактическая схема; при отсутствии ключа в хранилище подставляются дефолты):
```json
{
  "readout_speed": 500,
  "default_gain_mode": "1",
  "default_cooler_level": 1,
  "has_shutter": true,
  "sensor_name_override": "GreatEyes 9.0",
  "sdk_camera_address": "",
  "sdk_camera_port": 12345,
  "sdk_camera_interface": -1,
  "camera_index": 0,
  "temperature_hardware_option": 42223,
  "fits_export_bitpix": 32
}
```

### PUT `/settings`
Частичное обновление: передаются только изменяемые поля (`null` поля не меняют значение).

Request (пример):
```json
{
  "readout_speed": 1000,
  "fits_export_bitpix": 32,
  "sdk_camera_address": "192.168.31.234"
}
```

`fits_export_bitpix`: только `16` или `32` (см. экспорт FITS выше).

## 4. Внутренние интерфейсы (Python -> SDK)
Минимальные функции адаптера:
- `connect(camera_index: int) -> CameraInfo`
- `disconnect(camera_index: int) -> None`
- `set_camera_settings(...) -> CameraGeometry`
- `start_measurement(...) -> None`
- `is_busy() -> bool`
- `read_measurement() -> np.ndarray[uint16]`
- `stop_measurement() -> None`
- `set_cooler_power(on: bool, level: int | None) -> None`
- `set_target_temp(temp_c: int) -> None`
- `get_temperatures() -> TemperatureStatus`
- `get_capabilities() -> CameraCapabilities`
- `warmup(...) -> WarmupResult`

## 5. Политика ошибок
- Слой SDK возвращает `SdkError(code, message, raw_status)`.
- API маппит в `error_code`:
  - `NOT_CONNECTED`
  - `SDK_BUSY_TIMEOUT`
  - `SDK_CAMERA_ERROR`
  - `INVALID_PARAM`
  - `EXPOSURE_NOT_FOUND`
  - `INTERNAL_ERROR`
- ASCOM слой маппит API errors в ASCOM exceptions.

## 6. Версионирование контрактов
- API version в URL: `/api/v1`.
- Breaking changes только в `/v2`.
- JSON schema для request/response хранить в репозитории.
