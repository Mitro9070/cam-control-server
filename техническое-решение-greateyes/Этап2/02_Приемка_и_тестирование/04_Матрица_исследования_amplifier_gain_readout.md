# Матрица исследования amplifier/gain/readout (Sprint 4)

Дата: 2026-03-24

## 1) Цель

Подтвердить оптимальные режимы считывания для эксплуатационных сценариев:
- длительные спектры (приоритет шума),
- быстрая проверка/наведение (приоритет скорости).

## 2) Набор режимов

- Amplifier mode: `1`, `2` (для текущей камеры GreatEyes).
- Gain mode:
  - `0` = High capacity / max dynamic range,
  - `1` = Low noise / high sensitivity.
- Readout speed (kHz): `50`, `100`, `250`, `500`, `1000`, `3000`, `5000*`.
- Target temperature (C): `-10`, `-20`, `-40`, `-60`.

`*` 5000 kHz использовать как visualization/diagnostic режим, не как основной научный.

## 3) Паспортные ориентиры (Reserch)

Источник: `Reserch/greateyes_ELSE_i_Rev3.pdf`, `Reserch/GreateyesFlash.../include/greateyes.h`

| Параметр | Значение |
|---|---|
| Readout frequencies | 50/100/250/500/1000/3000/5000 kHz |
| Output nodes | 2 (для 1k1k/2k2k), 4 (для крупных моделей) |
| Temp sensors | CCD sensor + backside thermistor |
| Cooling limits | до -90/-100C (модельно-зависимо) |

## 4) Калибровочная таблица (этап 2, стартовая)

Статус: предварительное заполнение по паспорту/SDK, требует финального подтверждения на железе.

| Gain mode | Amplifier | Speed kHz | target_temp_c | gain_e_per_adu | read_noise_e_rms | Статус |
|---|---:|---:|---:|---:|---:|---|
| 0 (High capacity) | 1 | 50 | -20 | TBD | TBD | к измерению |
| 0 (High capacity) | 1 | 250 | -20 | TBD | TBD | к измерению |
| 0 (High capacity) | 1 | 1000 | -20 | TBD | TBD | к измерению |
| 1 (Low noise) | 1 | 50 | -20 | TBD | TBD | к измерению |
| 1 (Low noise) | 1 | 250 | -20 | TBD | TBD | к измерению |
| 1 (Low noise) | 1 | 1000 | -20 | TBD | TBD | к измерению |
| 0 (High capacity) | 2 | 250 | -20 | TBD | TBD | к измерению |
| 1 (Low noise) | 2 | 250 | -20 | TBD | TBD | к измерению |
| 1 (Low noise) | 2 | 3000 | -20 | TBD | TBD | к измерению |

## 5) Методика измерения

На каждую комбинацию:
1. 100 bias кадров.
2. 50 dark кадров (60s) и 50 dark (300s).
3. Измерить:
   - read noise RMS,
   - dark current trend,
   - time-to-readout,
   - равномерность по полю (для 2-усилительного режима).

## 6) Критерии выбора

- Профиль "Спектры": минимальный `read_noise_e_rms` и стабильность baseline.
- Профиль "Быстрый сервис": минимальный time-to-readout при приемлемом шуме.
