# Status Mapping (GreatEyes SDK)

Базовый mapping кодов статуса SDK (по имеющимся заголовкам/примерам):

- `0`: camera detected and ok
- `1`: no camera detected
- `2`: could not open USB device
- `3`: write config table failed
- `4`: write read request failed
- `5`: no trigger signal
- `6`: new camera detected
- `7`: unknown camera id
- `8`: parameter out of range
- `9`: no new data
- `10`: camera busy
- `11`: cooling turned off
- `12`: measurement stopped
- `13`: burst mode too much pixels
- `14`: timing table not found
- `15`: not critical
- `16`: illegal binning/crop combination

Используется для нормализации `SDK_CALL_FAILED` ошибок в Python adapter.
