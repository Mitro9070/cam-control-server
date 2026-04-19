const apiBase = "/api/v1";
const output = document.getElementById("output");
const activeExposureId = document.getElementById("activeExposureId");
const activeWarmupId = document.getElementById("activeWarmupId");
const uiHint = document.getElementById("uiHint");
const telemetryCanvas = document.getElementById("coolingTelemetryChart");
const telemetryCtx = telemetryCanvas ? telemetryCanvas.getContext("2d") : null;
const imagePreviewCanvas = document.getElementById("imagePreviewCanvas");
const imagePreviewCtx = imagePreviewCanvas ? imagePreviewCanvas.getContext("2d") : null;
const expProgressBar = document.getElementById("expProgressBar");
const expProgressText = document.getElementById("expProgressText");
const dashService = document.getElementById("dashService");
const dashConnected = document.getElementById("dashConnected");
const dashTemp = document.getElementById("dashTemp");
const dashTarget = document.getElementById("dashTarget");
const dashPower = document.getElementById("dashPower");
const dashExposure = document.getElementById("dashExposure");
const dashServiceSub = document.getElementById("dashServiceSub");
const dashCameraSub = document.getElementById("dashCameraSub");
const dashTempSub = document.getElementById("dashTempSub");
const dashTargetSub = document.getElementById("dashTargetSub");
const dashExposureSub = document.getElementById("dashExposureSub");
const dashPowerMeter = document.getElementById("dashPowerMeter");
const dashCardService = document.getElementById("dashCardService");
const dashCardCamera = document.getElementById("dashCardCamera");
const dashCardTemp = document.getElementById("dashCardTemp");
const dashCardTarget = document.getElementById("dashCardTarget");
const dashCardPower = document.getElementById("dashCardPower");
const dashCardExposure = document.getElementById("dashCardExposure");
const dashLedService = document.getElementById("dashLedService");
const dashLedCamera = document.getElementById("dashLedCamera");
const dashLedTemp = document.getElementById("dashLedTemp");
const dashLedExposure = document.getElementById("dashLedExposure");
const dashLedTarget = document.getElementById("dashLedTarget");
const dashLedPower = document.getElementById("dashLedPower");
const roiBinXInput = document.getElementById("roiBinX");
const roiBinYInput = document.getElementById("roiBinY");
const roiStartXInput = document.getElementById("roiStartX");
const roiStartYInput = document.getElementById("roiStartY");
const roiNumXInput = document.getElementById("roiNumX");
const roiNumYInput = document.getElementById("roiNumY");
const frameSummary = document.getElementById("frameSummary");
let telemetryAutoTimer = null;
let dashboardTimer = null;
let dashboardRefreshInFlight = false;

function log(title, data) {
  const rendered = typeof data === "string" ? data : JSON.stringify(data, null, 2);
  output.textContent = `[${new Date().toISOString()}] ${title}\n${rendered}\n`;
}

function logInfo(title, data) {
  log(`INFO: ${title}`, data);
}

function logWarn(title, data) {
  log(`WARNING: ${title}`, data);
}

async function callApi(method, path, body) {
  const opts = {
    method,
    headers: { "Content-Type": "application/json" },
  };
  if (body !== undefined) {
    opts.body = JSON.stringify(body);
  }

  const response = await fetch(`${apiBase}${path}`, opts);
  const text = await response.text();
  let json;
  try {
    json = text ? JSON.parse(text) : {};
  } catch {
    json = { raw: text };
  }
  if (!response.ok) {
    throw new Error(`${response.status}: ${JSON.stringify(json)}`);
  }
  return json;
}

function setUiHintText(text) {
  if (!uiHint) return;
  uiHint.textContent = `Подсказка: ${text}`;
}

function setFrameSummaryText(text) {
  if (!frameSummary) return;
  frameSummary.textContent = text;
}

function readIntegerInput(node, label) {
  const value = Number(node?.value);
  if (!Number.isFinite(value) || value < 0 || !Number.isInteger(value)) {
    throw new Error(`${label} должно быть целым числом`);
  }
  return value;
}

function setFrameInputBounds(caps) {
  if (!caps) return;
  const sensorX = Number(caps.camera_x_size);
  const sensorY = Number(caps.camera_y_size);
  const maxBinX = Math.max(1, Number(caps.max_binx || 1));
  const maxBinY = Math.max(1, Number(caps.max_biny || 1));
  const binX = Math.max(1, Number(roiBinXInput?.value || 1));
  const binY = Math.max(1, Number(roiBinYInput?.value || 1));
  const binnedWidth = Math.max(1, Math.floor(sensorX / binX));
  const binnedHeight = Math.max(1, Math.floor(sensorY / binY));
  if (roiBinXInput) roiBinXInput.max = String(maxBinX);
  if (roiBinYInput) roiBinYInput.max = String(maxBinY);
  if (roiStartXInput) roiStartXInput.max = String(Math.max(0, binnedWidth - 1));
  if (roiStartYInput) roiStartYInput.max = String(Math.max(0, binnedHeight - 1));
  if (roiNumXInput) roiNumXInput.max = String(binnedWidth);
  if (roiNumYInput) roiNumYInput.max = String(binnedHeight);
}

function setFrameFormValues(payload) {
  roiBinXInput.value = String(payload.bin_x);
  roiBinYInput.value = String(payload.bin_y);
  roiStartXInput.value = String(payload.start_x);
  roiStartYInput.value = String(payload.start_y);
  roiNumXInput.value = String(payload.num_x);
  roiNumYInput.value = String(payload.num_y);
}

function describeFrame(payload, caps) {
  const sensorPart =
    caps && Number.isFinite(Number(caps.camera_x_size)) && Number.isFinite(Number(caps.camera_y_size))
      ? ` | sensor ${caps.camera_x_size}x${caps.camera_y_size}`
      : "";
  const sensorRoiPart =
    caps
      ? ` | raw start ${payload.start_x * payload.bin_x},${payload.start_y * payload.bin_y}`
      : "";
  return `bin ${payload.bin_x}x${payload.bin_y} | start ${payload.start_x},${payload.start_y} | size ${payload.num_x}x${payload.num_y}${sensorPart}${sensorRoiPart}`;
}

function buildFramePayload(caps) {
  const payload = {
    bin_x: readIntegerInput(roiBinXInput, "Bin X"),
    bin_y: readIntegerInput(roiBinYInput, "Bin Y"),
    start_x: readIntegerInput(roiStartXInput, "Start X"),
    start_y: readIntegerInput(roiStartYInput, "Start Y"),
    num_x: readIntegerInput(roiNumXInput, "Num X"),
    num_y: readIntegerInput(roiNumYInput, "Num Y"),
  };
  if (payload.bin_x < 1 || payload.bin_y < 1) {
    throw new Error("Bin X / Bin Y должны быть >= 1");
  }
  if (payload.num_x < 1 || payload.num_y < 1) {
    throw new Error("Num X / Num Y должны быть >= 1");
  }
  if (caps) {
    const sensorX = Number(caps.camera_x_size);
    const sensorY = Number(caps.camera_y_size);
    const maxBinX = Number(caps.max_binx || 1);
    const maxBinY = Number(caps.max_biny || 1);
    const binnedWidth = Math.floor(sensorX / payload.bin_x);
    const binnedHeight = Math.floor(sensorY / payload.bin_y);
    if (payload.bin_x > maxBinX || payload.bin_y > maxBinY) {
      throw new Error(`Binning вне допустимого диапазона 1..${maxBinX} / 1..${maxBinY}`);
    }
    if (payload.start_x > Math.max(0, binnedWidth - 1)) {
      throw new Error(`StartX должен быть в диапазоне 0..${Math.max(0, binnedWidth - 1)} для bin ${payload.bin_x}`);
    }
    if (payload.start_y > Math.max(0, binnedHeight - 1)) {
      throw new Error(`StartY должен быть в диапазоне 0..${Math.max(0, binnedHeight - 1)} для bin ${payload.bin_y}`);
    }
    if (payload.start_x + payload.num_x > binnedWidth) {
      throw new Error(`ROI по X выходит за binned frame: StartX + NumX <= ${binnedWidth}`);
    }
    if (payload.start_y + payload.num_y > binnedHeight) {
      throw new Error(`ROI по Y выходит за binned frame: StartY + NumY <= ${binnedHeight}`);
    }
  }
  return payload;
}

function syncFrameFormToBinning(caps, { forceFullFrame = false } = {}) {
  if (!caps) return;
  const sensorX = Number(caps.camera_x_size);
  const sensorY = Number(caps.camera_y_size);
  const binX = Math.max(1, readIntegerInput(roiBinXInput, "Bin X"));
  const binY = Math.max(1, readIntegerInput(roiBinYInput, "Bin Y"));
  const binnedWidth = Math.max(1, Math.floor(sensorX / binX));
  const binnedHeight = Math.max(1, Math.floor(sensorY / binY));

  let startX = Math.max(0, Math.min(readIntegerInput(roiStartXInput, "Start X"), binnedWidth - 1));
  let startY = Math.max(0, Math.min(readIntegerInput(roiStartYInput, "Start Y"), binnedHeight - 1));
  let numX = readIntegerInput(roiNumXInput, "Num X");
  let numY = readIntegerInput(roiNumYInput, "Num Y");

  if (forceFullFrame) {
    startX = 0;
    startY = 0;
    numX = binnedWidth;
    numY = binnedHeight;
  } else {
    numX = Math.max(1, Math.min(numX, binnedWidth - startX));
    numY = Math.max(1, Math.min(numY, binnedHeight - startY));
  }

  setFrameFormValues({
    bin_x: binX,
    bin_y: binY,
    start_x: startX,
    start_y: startY,
    num_x: numX,
    num_y: numY,
  });
  setFrameInputBounds(caps);
  setFrameSummaryText(describeFrame({ bin_x: binX, bin_y: binY, start_x: startX, start_y: startY, num_x: numX, num_y: numY }, caps));
}

async function loadFrameCapabilities({ resetToFull = false } = {}) {
  await ensureConnected();
  const caps = await callApi("GET", "/camera/capabilities");
  setFrameInputBounds(caps);
  if (resetToFull) {
    setFrameFormValues({
      bin_x: 1,
      bin_y: 1,
      start_x: 0,
      start_y: 0,
      num_x: Number(caps.camera_x_size),
      num_y: Number(caps.camera_y_size),
    });
  }
  try {
    syncFrameFormToBinning(caps, { forceFullFrame: resetToFull });
  } catch {
    setFrameSummaryText(`sensor ${caps.camera_x_size}x${caps.camera_y_size} | заполните параметры ROI`);
  }
  return caps;
}

function setButtonLoading(button, loading, loadingText) {
  if (!button) return;
  if (loading) {
    if (!button.dataset.originalText) {
      button.dataset.originalText = button.textContent;
    }
    button.classList.add("is-loading");
    if (loadingText) {
      button.textContent = loadingText;
    }
    return;
  }
  button.classList.remove("is-loading");
  if (button.dataset.originalText) {
    button.textContent = button.dataset.originalText;
    delete button.dataset.originalText;
  }
}

function bindClick(id, handler, opts = {}) {
  document.getElementById(id).addEventListener("click", async () => {
    const btn = document.getElementById(id);
    const loadingText = opts.loadingText || "Выполняется...";
    setButtonLoading(btn, true, loadingText);
    try {
      await handler();
      if (opts.successHint) {
        setUiHintText(opts.successHint);
      }
    } catch (error) {
      log("ERROR", String(error));
      if (opts.errorHint) {
        setUiHintText(opts.errorHint);
      }
    } finally {
      setButtonLoading(btn, false);
    }
  });
}

function setDashboardValue(node, value, statusClass) {
  if (!node) return;
  node.textContent = value;
  node.classList.remove("status-ok", "status-warn", "status-error");
  if (statusClass) {
    node.classList.add(statusClass);
  }
}

/** API возвращает ccd_temp_c; старый UI ошибочно читал current_temp_c → NaN. */
function readCcdTempC(cooling) {
  if (!cooling || typeof cooling !== "object") return null;
  const raw = cooling.ccd_temp_c ?? cooling.current_temp_c ?? cooling.ccd_temp;
  const n = Number(raw);
  return Number.isFinite(n) ? n : null;
}

function readTargetTempC(cooling) {
  if (!cooling || typeof cooling !== "object") return null;
  const n = Number(cooling.target_temp_c);
  return Number.isFinite(n) ? n : null;
}

function readCoolerPowerPercent(cooling) {
  if (!cooling || typeof cooling !== "object") return null;
  const n = Number(cooling.cooler_power_percent);
  return Number.isFinite(n) ? n : null;
}

function formatTempDisplay(celsius, decimals = 1) {
  if (celsius === null || celsius === undefined || !Number.isFinite(Number(celsius))) {
    return "—";
  }
  const v = Number(celsius);
  const sign = v < 0 ? "−" : "";
  return `${sign}${Math.abs(v).toFixed(decimals)} °C`;
}

function setDashCard(card, tone) {
  if (!card) return;
  card.dataset.tone = tone || "neutral";
}

function setDashLed(led, on, pulseClass = "is-pulse") {
  if (!led) return;
  led.classList.toggle(pulseClass, !!on);
}

function setPowerMeter(percent) {
  if (!dashPowerMeter) return;
  const p = Number(percent);
  const w = Number.isFinite(p) ? Math.min(100, Math.max(0, p)) : 0;
  dashPowerMeter.style.width = `${w}%`;
}

function exposureDashTone(state) {
  if (state === "completed") return "ok";
  if (state === "running" || state === "exposing") return "warn";
  if (state === "error" || state === "aborted") return "danger";
  return "neutral";
}

function updateDashExposureMain(state, percent) {
  const pct = Number.isFinite(Number(percent)) ? Number(percent) : 0;
  const st = (state || "idle").toLowerCase();
  if (st === "idle" || !state) {
    setDashboardValue(dashExposure, "IDLE", "");
    if (dashExposureSub) dashExposureSub.textContent = "нет активного кадра";
    setDashCard(dashCardExposure, "neutral");
    setDashLed(dashLedExposure, false);
    return;
  }
  const line = `${st.toUpperCase()} · ${pct.toFixed(0)}%`;
  const tone = exposureDashTone(st);
  setDashboardValue(
    dashExposure,
    line,
    tone === "ok" ? "status-ok" : tone === "danger" ? "status-error" : "status-warn"
  );
  if (dashExposureSub) {
    dashExposureSub.textContent =
      st === "running" ? "интеграция / считывание" : st === "completed" ? "кадр в буфере" : "";
  }
  setDashCard(dashCardExposure, tone);
  setDashLed(dashLedExposure, st === "running" || st === "exposing");
}

function drawCoolingTelemetry(points) {
  if (!telemetryCtx || !telemetryCanvas) return;
  const ctx = telemetryCtx;
  const width = telemetryCanvas.width;
  const height = telemetryCanvas.height;
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#0f1520";
  ctx.fillRect(0, 0, width, height);
  if (!points || points.length < 2) {
    ctx.fillStyle = "#9eb0cf";
    ctx.font = "13px Segoe UI";
    ctx.fillText("Недостаточно данных телеметрии", 12, 22);
    return;
  }

  const temps = points.map((p) => Number(p.ccd_temp_c));
  const powers = points.map((p) => Number(p.cooler_power_percent));
  const tMin = Math.min(...temps);
  const tMax = Math.max(...temps);
  const tPad = Math.max(1, (tMax - tMin) * 0.2);
  const tempLow = tMin - tPad;
  const tempHigh = tMax + tPad;

  const xOf = (idx) => 40 + (idx * (width - 60)) / (points.length - 1);
  const yTemp = (v) => height - 24 - ((v - tempLow) / Math.max(1e-6, tempHigh - tempLow)) * (height - 48);
  const yPower = (v) => height - 24 - (v / 100) * (height - 48);

  // Grid
  ctx.strokeStyle = "#273043";
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const y = 24 + (i * (height - 48)) / 4;
    ctx.beginPath();
    ctx.moveTo(40, y);
    ctx.lineTo(width - 20, y);
    ctx.stroke();
  }

  // Temperature curve
  ctx.strokeStyle = "#5fb3ff";
  ctx.lineWidth = 2;
  ctx.beginPath();
  points.forEach((p, i) => {
    const x = xOf(i);
    const y = yTemp(Number(p.ccd_temp_c));
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  // Power curve
  ctx.strokeStyle = "#77dd77";
  ctx.lineWidth = 2;
  ctx.beginPath();
  points.forEach((p, i) => {
    const x = xOf(i);
    const y = yPower(Number(p.cooler_power_percent));
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  ctx.fillStyle = "#9eb0cf";
  ctx.font = "12px Segoe UI";
  ctx.fillText(`CCD temp (C): ${temps[temps.length - 1]}`, 10, height - 6);
  ctx.fillText(`Cooler power (%): ${powers[powers.length - 1]}`, 220, height - 6);
}

function decodeU16Base64(base64Data) {
  const bytes = atob(base64Data || "");
  const out = new Uint16Array(Math.floor(bytes.length / 2));
  for (let i = 0; i < out.length; i++) {
    const lo = bytes.charCodeAt(i * 2);
    const hi = bytes.charCodeAt(i * 2 + 1);
    out[i] = (hi << 8) | lo;
  }
  return out;
}

function drawImagePreview(width, height, base64Data) {
  if (!imagePreviewCtx || !imagePreviewCanvas) return;
  const data = decodeU16Base64(base64Data);
  if (!data.length || width <= 0 || height <= 0) return;
  let min = Number.MAX_SAFE_INTEGER;
  let max = 0;
  for (let i = 0; i < data.length; i++) {
    const v = data[i];
    if (v < min) min = v;
    if (v > max) max = v;
  }
  const span = Math.max(1, max - min);
  const img = imagePreviewCtx.createImageData(width, height);
  for (let i = 0; i < data.length; i++) {
    const gray = Math.max(0, Math.min(255, Math.round(((data[i] - min) / span) * 255)));
    img.data[i * 4] = gray;
    img.data[i * 4 + 1] = gray;
    img.data[i * 4 + 2] = gray;
    img.data[i * 4 + 3] = 255;
  }

  const offscreen = document.createElement("canvas");
  offscreen.width = width;
  offscreen.height = height;
  offscreen.getContext("2d").putImageData(img, 0, 0);

  imagePreviewCtx.clearRect(0, 0, imagePreviewCanvas.width, imagePreviewCanvas.height);
  imagePreviewCtx.fillStyle = "#0f1520";
  imagePreviewCtx.fillRect(0, 0, imagePreviewCanvas.width, imagePreviewCanvas.height);
  const scale = Math.min(imagePreviewCanvas.width / width, imagePreviewCanvas.height / height);
  const drawW = Math.max(1, Math.round(width * scale));
  const drawH = Math.max(1, Math.round(height * scale));
  const drawX = Math.round((imagePreviewCanvas.width - drawW) / 2);
  const drawY = Math.round((imagePreviewCanvas.height - drawH) / 2);
  imagePreviewCtx.drawImage(offscreen, drawX, drawY, drawW, drawH);
}

function setExposureProgress(percent, label) {
  const safePercent = Math.max(0, Math.min(100, Number.isFinite(percent) ? Number(percent) : 0));
  if (expProgressBar) {
    expProgressBar.style.width = `${safePercent}%`;
  }
  if (expProgressText) {
    expProgressText.textContent = label || `Прогресс экспозиции: ${safePercent.toFixed(0)}%`;
  }
}

async function getCameraState() {
  return callApi("GET", "/camera/state");
}

async function ensureConnected() {
  const state = await getCameraState();
  if (state.connected) {
    return state;
  }
  const connectResult = await callApi("POST", "/camera/connect", {});
  logInfo("Камера была автоматически подключена (Auto connect)", connectResult);
  return getCameraState();
}

function getExposureId() {
  const id = activeExposureId.textContent;
  return id === "none" ? null : id;
}

async function ensureImageReadyWithProgress() {
  const state = await getCameraState();
  if (!state.active_exposure_id) {
    setExposureProgress(100, "Активной экспозиции нет");
    return;
  }
  activeExposureId.textContent = state.active_exposure_id;
  const exposureId = state.active_exposure_id;
  for (let i = 0; i < 120; i++) {
    const status = await callApi("GET", `/camera/exposures/${exposureId}/status`);
    const pct = Number(status.percent ?? 0);
    setExposureProgress(pct, `Прогресс экспозиции: ${pct.toFixed(0)}% (${status.state})`);
    updateDashExposureMain(status.state, pct);
    if (status.image_ready || status.state === "completed") {
      setExposureProgress(100, "Кадр готов");
      return;
    }
    if (status.state === "error" || status.state === "aborted" || status.state === "stopped") {
      throw new Error(`Экспозиция завершилась со статусом: ${status.state}`);
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error("Таймаут ожидания кадра");
}

async function refreshDashboard() {
  if (dashboardRefreshInFlight) return;
  dashboardRefreshInFlight = true;
  try {
    try {
      const health = await callApi("GET", "/health");
      const db = String(health.db || "—");
      const apiOk = health.status === "ok";
      setDashboardValue(dashService, apiOk ? "ONLINE" : "DEGRADED", apiOk ? "status-ok" : "status-warn");
      if (dashServiceSub) {
        dashServiceSub.textContent =
          db === "connected" ? "PostgreSQL · связь" : db === "local" ? "хранилище · local" : `PostgreSQL · ${db}`;
      }
      const dbTone =
        db === "connected" || db === "local" ? "ok" : apiOk ? "warn" : "danger";
      setDashCard(dashCardService, dbTone);
      setDashLed(dashLedService, apiOk);
    } catch {
      setDashboardValue(dashService, "OFFLINE", "status-error");
      if (dashServiceSub) dashServiceSub.textContent = "API недоступен";
      setDashCard(dashCardService, "danger");
      setDashLed(dashLedService, false);
    }

    try {
      const state = await getCameraState();
      const linked = !!state.connected;
      setDashboardValue(
        dashConnected,
        linked ? "LINK" : "NO LINK",
        linked ? "status-ok" : "status-error"
      );
      if (dashCameraSub) {
        dashCameraSub.textContent = linked ? "сессия активна" : "подключите камеру";
      }
      setDashCard(dashCardCamera, linked ? "ok" : "danger");
      setDashLed(dashLedCamera, linked);

      if (state.active_exposure_id) {
        activeExposureId.textContent = state.active_exposure_id;
        try {
          const exp = await callApi("GET", `/camera/exposures/${state.active_exposure_id}/status`);
          const pct = Number(exp.percent ?? 0);
          updateDashExposureMain(exp.state, pct);
          setExposureProgress(pct, `Прогресс экспозиции: ${pct.toFixed(0)}% (${exp.state})`);
        } catch {
          setDashboardValue(dashExposure, "UNKNOWN", "status-warn");
          if (dashExposureSub) dashExposureSub.textContent = "статус недоступен";
          setDashCard(dashCardExposure, "warn");
          setDashLed(dashLedExposure, false);
        }
      } else {
        updateDashExposureMain("idle", 0);
        setExposureProgress(0, "Прогресс экспозиции: 0%");
      }

      if (state.connected) {
        try {
          const cooling = await callApi("GET", "/camera/cooling/status");
          const ccd = readCcdTempC(cooling);
          const tgt = readTargetTempC(cooling);
          const pwr = readCoolerPowerPercent(cooling);
          const coolerOn = !!cooling.cooler_on;

          setDashboardValue(dashTemp, formatTempDisplay(ccd), ccd !== null ? "status-ok" : "status-warn");
          if (dashTempSub) {
            if (ccd !== null) {
              const chip = Number(cooling.backside_temp_c);
              const chipStr = Number.isFinite(chip) ? `backside ${formatTempDisplay(chip, 1)}` : "CCD";
              dashTempSub.textContent = chipStr;
            } else {
              dashTempSub.textContent = "данные сенсора не пришли";
            }
          }
          const tempTone =
            ccd === null ? "warn" : ccd <= -5 ? "ok" : ccd >= 18 ? "warn" : "neutral";
          setDashCard(dashCardTemp, tempTone);
          setDashLed(dashLedTemp, ccd !== null);

          setDashboardValue(dashTarget, formatTempDisplay(tgt), coolerOn ? "status-warn" : "");
          if (dashTargetSub) {
            dashTargetSub.textContent = coolerOn ? "охладитель ON" : "охладитель OFF";
          }
          setDashCard(dashCardTarget, coolerOn ? "warn" : "neutral");
          setDashLed(dashLedTarget, coolerOn);

          const pStr = pwr !== null ? `${pwr.toFixed(0)} %` : "—";
          setDashboardValue(dashPower, pStr, pwr !== null && pwr > 0 ? "status-ok" : "status-warn");
          setPowerMeter(pwr ?? 0);
          setDashCard(dashCardPower, pwr !== null && pwr > 5 ? "ok" : "neutral");
          setDashLed(dashLedPower, (pwr ?? 0) > 0);
        } catch {
          setDashboardValue(dashTemp, "—", "status-warn");
          if (dashTempSub) dashTempSub.textContent = "опрос охлаждения не удался";
          setDashCard(dashCardTemp, "warn");
          setDashLed(dashLedTemp, false);
          setDashboardValue(dashTarget, "—", "status-warn");
          if (dashTargetSub) dashTargetSub.textContent = "";
          setDashCard(dashCardTarget, "neutral");
          setDashLed(dashLedTarget, false);
          setDashboardValue(dashPower, "—", "status-warn");
          setPowerMeter(0);
          setDashCard(dashCardPower, "neutral");
          setDashLed(dashLedPower, false);
        }
      } else {
        setDashboardValue(dashTemp, "—");
        if (dashTempSub) dashTempSub.textContent = "камера не подключена";
        setDashCard(dashCardTemp, "neutral");
        setDashLed(dashLedTemp, false);
        setDashboardValue(dashTarget, "—");
        if (dashTargetSub) dashTargetSub.textContent = "";
        setDashCard(dashCardTarget, "neutral");
        setDashLed(dashLedTarget, false);
        setDashboardValue(dashPower, "—");
        setPowerMeter(0);
        setDashCard(dashCardPower, "neutral");
        setDashLed(dashLedPower, false);
      }
    } catch {
      setDashboardValue(dashConnected, "—", "status-warn");
      if (dashCameraSub) dashCameraSub.textContent = "состояние неизвестно";
      setDashCard(dashCardCamera, "warn");
      setDashLed(dashLedCamera, false);
      setDashboardValue(dashExposure, "—", "status-warn");
      if (dashExposureSub) dashExposureSub.textContent = "";
      setDashCard(dashCardExposure, "warn");
      setDashboardValue(dashTemp, "—");
      setDashboardValue(dashTarget, "—");
      setDashboardValue(dashPower, "—");
      setPowerMeter(0);
    }
  } finally {
    dashboardRefreshInFlight = false;
  }
}

function startDashboardAutoRefresh() {
  if (dashboardTimer) {
    clearInterval(dashboardTimer);
  }
  dashboardTimer = setInterval(() => {
    refreshDashboard().catch(() => {
      // Best effort dashboard refresh.
    });
  }, 2500);
}

function switchTab(tabName) {
  document.querySelectorAll(".tab").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tab === tabName);
  });
  document.querySelectorAll(".panel").forEach((panel) => {
    panel.classList.toggle("active", panel.id === `tab-${tabName}`);
  });
}

function selectedProfileId() {
  const select = document.getElementById("profileSelect");
  return select.value || null;
}

function fillProfileSelect(items) {
  const select = document.getElementById("profileSelect");
  select.innerHTML = "";
  items.forEach((item) => {
    const option = document.createElement("option");
    option.value = item.profile_id;
    option.textContent = `${item.name}${item.is_active ? " (active)" : ""}`;
    select.appendChild(option);
  });
}

function loadProfileToForm(profile) {
  if (!profile) return;
  document.getElementById("profileName").value = profile.name || "";
  document.getElementById("profileAddress").value = profile.sdk_camera_address || "";
  document.getElementById("profilePort").value = profile.sdk_camera_port ?? 12345;
  document.getElementById("profileInterface").value = profile.sdk_camera_interface ?? -1;
  document.getElementById("profileIndex").value = profile.sdk_camera_index ?? 0;
  document.getElementById("profileTempOption").value = profile.temperature_hardware_option ?? 42223;
  document.getElementById("setReadoutSpeed").value = String(profile.readout_speed ?? 1000);
  document.getElementById("setGainMode").value = String(profile.gain_mode ?? "1");
}

document.querySelectorAll(".tab").forEach((button) => {
  button.addEventListener("click", () => switchTab(button.dataset.tab));
});

[roiBinXInput, roiBinYInput].forEach((node) => {
  node?.addEventListener("change", async () => {
    try {
      const caps = await loadFrameCapabilities();
      syncFrameFormToBinning(caps, { forceFullFrame: true });
      setUiHintText("Binning изменен: размер frame автоматически приведен к полному binned кадру.");
    } catch {
      setFrameSummaryText("Для авторасчета frame подключите камеру и запросите sensor size.");
    }
  });
});

[roiStartXInput, roiStartYInput, roiNumXInput, roiNumYInput].forEach((node) => {
  node?.addEventListener("change", async () => {
    try {
      const caps = await loadFrameCapabilities();
      syncFrameFormToBinning(caps);
    } catch {
      // Best-effort summary refresh when API is unavailable.
    }
  });
});

// Connection
bindClick("btnHealth", async () => logInfo("Проверка сервиса (Health)", await callApi("GET", "/health")));
bindClick("btnState", async () => logInfo("Состояние камеры (State)", await getCameraState()));
bindClick(
  "btnConnect",
  async () => {
    logInfo("Подключить (Connect)", await callApi("POST", "/camera/connect", {}));
    await loadFrameCapabilities({ resetToFull: true });
    await refreshDashboard();
  },
  {
    loadingText: "Подключение...",
    successHint: "Камера подключена. Следующий шаг: проверьте capabilities или запустите экспозицию.",
    errorHint: "Подключение не удалось. Проверьте IP/порт камеры и занятость SDK.",
  }
);
bindClick(
  "btnDisconnect",
  async () => {
    logInfo("Отключить (Disconnect)", await callApi("POST", "/camera/disconnect", {}));
    await refreshDashboard();
  },
  {
    loadingText: "Отключение...",
    successHint: "Камера отключена. Можно переключить профиль и подключиться снова.",
  }
);
bindClick("btnCapabilities", async () => {
  await ensureConnected();
  const caps = await callApi("GET", "/camera/capabilities");
  setFrameInputBounds(caps);
  setFrameSummaryText(describeFrame(buildFramePayload(caps), caps));
  logInfo("Возможности камеры (Capabilities)", caps);
});

bindClick("btnFrameLoadCaps", async () => {
  const caps = await loadFrameCapabilities();
  logInfo("Размер сенсора / ROI bounds", caps);
}, { loadingText: "Чтение sensor size..." });

bindClick("btnFrameApply", async () => {
  const caps = await loadFrameCapabilities();
  const payload = buildFramePayload(caps);
  const response = await callApi("PUT", "/camera/config/roi-binning", payload);
  setFrameSummaryText(describeFrame(payload, caps));
  setUiHintText("Frame/Subframe применен. Можно запускать экспозицию или смотреть latest image.");
  logInfo("ROI / Subframe applied", { ...payload, response });
}, { loadingText: "Применение ROI..." });

bindClick("btnFrameFull", async () => {
  const caps = await loadFrameCapabilities({ resetToFull: true });
  const payload = buildFramePayload(caps);
  const response = await callApi("PUT", "/camera/config/roi-binning", payload);
  setFrameSummaryText(describeFrame(payload, caps));
  setUiHintText("Возвращен полный кадр 1x1.");
  logInfo("Full frame applied", { ...payload, response });
}, { loadingText: "Сброс ROI..." });

// Exposure
bindClick("btnExposureStart", async () => {
  await ensureConnected();
  const payload = {
    duration_sec: Number(document.getElementById("expDuration").value),
    light: document.getElementById("expLight").checked,
  };
  if (!Number.isFinite(payload.duration_sec) || payload.duration_sec <= 0) {
    throw new Error("Некорректная длительность экспозиции (Duration must be > 0)");
  }
  const data = await callApi("POST", "/camera/exposures", payload);
  activeExposureId.textContent = data.exposure_id;
  setExposureProgress(Number(data.percent ?? 0), `Прогресс экспозиции: ${Number(data.percent ?? 0).toFixed(0)}% (${data.state})`);
  setUiHintText("Экспозиция запущена. Нажмите Статус или Последний кадр.");
  await refreshDashboard();
  logInfo("Старт экспозиции (Start)", data);
}, { loadingText: "Запуск экспозиции..." });

bindClick("btnExposureStatus", async () => {
  const exposureId = getExposureId();
  if (!exposureId) {
    const state = await getCameraState();
    if (state.active_exposure_id) {
      activeExposureId.textContent = state.active_exposure_id;
    } else {
      logWarn("Нет активной экспозиции (No active exposure id)", state);
      return;
    }
  }
  const currentExposureId = getExposureId();
  if (!currentExposureId) return;
  const data = await callApi("GET", `/camera/exposures/${currentExposureId}/status`);
  const pct = Number(data.percent ?? 0);
  setExposureProgress(pct, `Прогресс экспозиции: ${pct.toFixed(0)}% (${data.state})`);
  if (data.image_ready) {
    logInfo("Статус экспозиции: кадр готов (Status)", data);
  } else {
    logInfo("Статус экспозиции: кадр еще готовится (Status)", data);
  }
  await refreshDashboard();
}, { loadingText: "Проверка статуса..." });

bindClick("btnExposureStop", async () => {
  const exposureId = getExposureId();
  if (!exposureId) {
    logWarn("Остановить нельзя: нет активной экспозиции (Stop)", {});
    return;
  }
  const data = await callApi("POST", `/camera/exposures/${exposureId}/stop`, {});
  logInfo("Остановить экспозицию (Stop)", data);
});

bindClick("btnExposureAbort", async () => {
  const exposureId = getExposureId();
  if (!exposureId) {
    logWarn("Прервать нельзя: нет активной экспозиции (Abort)", {});
    return;
  }
  const data = await callApi("POST", `/camera/exposures/${exposureId}/abort`, {});
  logInfo("Прервать экспозицию (Abort)", data);
});

bindClick("btnImageLatest", async () => {
  const state = await getCameraState();
  if (!state.image_ready) {
    await ensureImageReadyWithProgress();
  }
  try {
    const data = await callApi("GET", "/camera/images/latest");
    logInfo("Последний кадр (Latest image)", data);
    setUiHintText("Кадр успешно получен. Можно посмотреть метаданные или экспортировать в FITS.");
  } catch (error) {
    // Защита на случай гонки состояния между state и latest image.
    logWarn("Пока нет доступного кадра (Latest image)", String(error));
  }
  await refreshDashboard();
}, { loadingText: "Получение кадра..." });

bindClick("btnImageMetadata", async () => {
  await ensureConnected();
  const data = await callApi("GET", "/camera/images/latest/metadata");
  logInfo("Метаданные изображения (Metadata)", data);
});

bindClick("btnImageShowLatest", async () => {
  await ensureConnected();
  await ensureImageReadyWithProgress();
  const data = await callApi("GET", "/camera/images/latest");
  if (data.pixel_data_base64) {
    drawImagePreview(Number(data.width), Number(data.height), data.pixel_data_base64);
  }
  logInfo("Последний кадр (Show latest)", {
    exposure_id: data.exposure_id,
    width: data.width,
    height: data.height,
    sample_pixels: data.sample_pixels,
  });
  await refreshDashboard();
}, { loadingText: "Загрузка кадра..." });

bindClick("btnImageResize", async () => {
  await ensureConnected();
  const payload = {
    width: Number(document.getElementById("imgResizeWidth").value),
    height: Number(document.getElementById("imgResizeHeight").value),
  };
  const data = await callApi("POST", "/camera/images/latest/resize", payload);
  drawImagePreview(Number(data.width), Number(data.height), data.pixel_data_base64);
  logInfo("Resize изображения", { width: data.width, height: data.height, sample_pixels: data.sample_pixels });
});

bindClick("btnImageExportFits", async () => {
  await ensureConnected();
  const payload = { file_name: document.getElementById("fitsFileName").value.trim() || "latest_image.fits" };
  const data = await callApi("POST", "/camera/images/latest/export/fits", payload);
  logInfo("FITS экспорт", data);
});

// Cooling
bindClick("btnCoolingStatus", async () => {
  await ensureConnected();
  logInfo("Статус охлаждения (Status)", await callApi("GET", "/camera/cooling/status"));
  await refreshDashboard();
}, { loadingText: "Опрос охлаждения..." });

bindClick("btnCoolingPower", async () => {
  await ensureConnected();
  const payload = {
    cooler_on: document.getElementById("coolerOn").checked,
    cooler_power_percent: Number(document.getElementById("coolerPower").value),
  };
  if (payload.cooler_power_percent < 0 || payload.cooler_power_percent > 100) {
    throw new Error("Мощность охладителя должна быть в диапазоне 0..100");
  }
  logInfo("Установить мощность (Set power)", await callApi("PUT", "/camera/cooling/power", payload));
  await refreshDashboard();
}, { loadingText: "Применение..." });

bindClick("btnCoolingTarget", async () => {
  await ensureConnected();
  const payload = {
    target_temp_c: Number(document.getElementById("targetTemp").value),
  };
  if (!Number.isFinite(payload.target_temp_c)) {
    throw new Error("Некорректная целевая температура (Target)");
  }
  logInfo("Установить целевую температуру (Set target)", await callApi("PUT", "/camera/cooling/target", payload));
  await refreshDashboard();
}, { loadingText: "Установка цели..." });

bindClick("btnCoolingControllerStatus", async () => {
  await ensureConnected();
  const status = await callApi("GET", "/camera/cooling/controller/status");
  document.getElementById("coolingMode").value = status.mode;
  logInfo("Контроллер охлаждения (Status)", status);
  await refreshDashboard();
}, { loadingText: "Опрос контроллера..." });

bindClick("btnCoolingControllerMode", async () => {
  await ensureConnected();
  const mode = document.getElementById("coolingMode").value;
  const status = await callApi("PUT", "/camera/cooling/controller/mode", { mode });
  logInfo("Контроллер охлаждения (Set mode)", status);
  await refreshDashboard();
}, { loadingText: "Применение профиля..." });

bindClick("btnWarmupStart", async () => {
  await ensureConnected();
  const parseLocaleNumber = (raw) => Number(String(raw).replace(",", "."));
  const payload = {
    target_temp_c: parseLocaleNumber(document.getElementById("warmTarget").value),
    temp_step_c: parseLocaleNumber(document.getElementById("warmStepTemp").value),
    power_step_percent: parseLocaleNumber(document.getElementById("warmStepPower").value),
    step_interval_sec: parseLocaleNumber(document.getElementById("warmStepInterval").value),
  };
  if (!Number.isFinite(payload.target_temp_c) || !Number.isFinite(payload.temp_step_c) || !Number.isFinite(payload.power_step_percent) || !Number.isFinite(payload.step_interval_sec)) {
    throw new Error("Параметры warm-up должны быть корректными числами");
  }
  if (payload.temp_step_c <= 0 || payload.power_step_percent <= 0 || payload.step_interval_sec <= 0) {
    throw new Error("Параметры warm-up должны быть больше 0");
  }
  const data = await callApi("POST", "/camera/cooling/warmup", payload);
  activeWarmupId.textContent = data.warmup_job_id;
  logInfo("Старт прогрева (Start warm-up)", data);
});

bindClick("btnWarmupStatus", async () => {
  const warmupId = activeWarmupId.textContent;
  if (warmupId === "none") {
    logWarn("Нет ID прогрева (No warm-up id)", {});
    return;
  }
  const data = await callApi("GET", `/camera/cooling/warmup/${warmupId}`);
  logInfo("Статус прогрева (Warm-up status)", data);
});

// Settings
bindClick("btnProfilesLoad", async () => {
  const data = await callApi("GET", "/camera/profiles");
  fillProfileSelect(data.items || []);
  const active = (data.items || []).find((p) => p.is_active) || (data.items || [])[0];
  if (active) {
    document.getElementById("profileSelect").value = active.profile_id;
    loadProfileToForm(active);
  }
  logInfo("Профили камеры (Profiles)", data);
});

bindClick("btnProfileCreate", async () => {
  const payload = {
    name: document.getElementById("profileName").value.trim(),
    sdk_camera_address: document.getElementById("profileAddress").value.trim(),
    sdk_camera_port: Number(document.getElementById("profilePort").value),
    sdk_camera_interface: Number(document.getElementById("profileInterface").value),
    sdk_camera_index: Number(document.getElementById("profileIndex").value),
    temperature_hardware_option: Number(document.getElementById("profileTempOption").value),
    readout_speed: Number(document.getElementById("setReadoutSpeed").value),
    gain_mode: document.getElementById("setGainMode").value,
  };
  const created = await callApi("POST", "/camera/profiles", payload);
  const list = await callApi("GET", "/camera/profiles");
  fillProfileSelect(list.items || []);
  document.getElementById("profileSelect").value = created.profile_id;
  logInfo("Профиль создан (Create profile)", created);
});

bindClick("btnProfileUpdate", async () => {
  const profileId = selectedProfileId();
  if (!profileId) throw new Error("Сначала выберите профиль");
  const payload = {
    name: document.getElementById("profileName").value.trim(),
    sdk_camera_address: document.getElementById("profileAddress").value.trim(),
    sdk_camera_port: Number(document.getElementById("profilePort").value),
    sdk_camera_interface: Number(document.getElementById("profileInterface").value),
    sdk_camera_index: Number(document.getElementById("profileIndex").value),
    temperature_hardware_option: Number(document.getElementById("profileTempOption").value),
    readout_speed: Number(document.getElementById("setReadoutSpeed").value),
    gain_mode: document.getElementById("setGainMode").value,
  };
  const updated = await callApi("PUT", `/camera/profiles/${profileId}`, payload);
  const list = await callApi("GET", "/camera/profiles");
  fillProfileSelect(list.items || []);
  document.getElementById("profileSelect").value = profileId;
  logInfo("Профиль обновлен (Update profile)", updated);
});

bindClick("btnProfileActivate", async () => {
  const profileId = selectedProfileId();
  if (!profileId) throw new Error("Сначала выберите профиль");
  const activated = await callApi("POST", `/camera/profiles/${profileId}/activate`, {});
  const list = await callApi("GET", "/camera/profiles");
  fillProfileSelect(list.items || []);
  document.getElementById("profileSelect").value = profileId;
  loadProfileToForm(activated);
  logInfo("Профиль активирован (Activate profile)", activated);
});

bindClick("btnSettingsLoad", async () => {
  const data = await callApi("GET", "/settings");
  document.getElementById("setReadoutSpeed").value = String(data.readout_speed);
  document.getElementById("setGainMode").value = data.default_gain_mode;
  document.getElementById("setCoolerLevel").value = data.default_cooler_level;
  document.getElementById("setHasShutter").checked = data.has_shutter;
  document.getElementById("setSensorName").value = data.sensor_name_override;
  document.getElementById("profileAddress").value = data.sdk_camera_address || "";
  document.getElementById("profilePort").value = data.sdk_camera_port ?? 12345;
  document.getElementById("profileInterface").value = data.sdk_camera_interface ?? -1;
  document.getElementById("profileIndex").value = data.camera_index ?? 0;
  document.getElementById("profileTempOption").value = data.temperature_hardware_option ?? 42223;
  document.getElementById("setFitsExportBitpix").value = String(data.fits_export_bitpix ?? 32);
  logInfo("Загрузить настройки (Load settings)", data);
});

bindClick("btnSettingsSave", async () => {
  const payload = {
    readout_speed: Number(document.getElementById("setReadoutSpeed").value),
    default_gain_mode: document.getElementById("setGainMode").value,
    default_cooler_level: Number(document.getElementById("setCoolerLevel").value),
    has_shutter: document.getElementById("setHasShutter").checked,
    sensor_name_override: document.getElementById("setSensorName").value,
    sdk_camera_address: document.getElementById("profileAddress").value.trim(),
    sdk_camera_port: Number(document.getElementById("profilePort").value),
    sdk_camera_interface: Number(document.getElementById("profileInterface").value),
    camera_index: Number(document.getElementById("profileIndex").value),
    temperature_hardware_option: Number(document.getElementById("profileTempOption").value),
    fits_export_bitpix: Number(document.getElementById("setFitsExportBitpix").value),
  };
  logInfo("Сохранить настройки (Save settings)", await callApi("PUT", "/settings", payload));
});

// Logs
bindClick("btnLogsLoad", async () => {
  const limit = Number(document.getElementById("logsLimit").value);
  logInfo("Загрузить логи (Load logs)", await callApi("GET", `/logs/events?limit=${limit}`));
});

bindClick("btnCoolingTelemetryLoad", async () => {
  await ensureConnected();
  const data = await callApi("GET", "/camera/cooling/telemetry?limit=120");
  drawCoolingTelemetry(data.items || []);
  logInfo("Температурная телеметрия (Cooling telemetry)", {
    samples: (data.items || []).length,
    last: (data.items || [])[Math.max(0, (data.items || []).length - 1)] || null,
  });
});

bindClick("btnCoolingTelemetryAuto", async () => {
  const btn = document.getElementById("btnCoolingTelemetryAuto");
  if (telemetryAutoTimer) {
    clearInterval(telemetryAutoTimer);
    telemetryAutoTimer = null;
    btn.textContent = "Автообновление: off";
    return;
  }
  btn.textContent = "Автообновление: on";
  telemetryAutoTimer = setInterval(async () => {
    try {
      const data = await callApi("GET", "/camera/cooling/telemetry?limit=120");
      drawCoolingTelemetry(data.items || []);
    } catch {
      // Best effort for UI graph.
    }
  }, 2000);
  document.getElementById("btnCoolingTelemetryLoad").click();
});

logInfo("Готово (Ready)", { message: "UI loaded", apiBase });
document.getElementById("btnProfilesLoad").click();
refreshDashboard().catch(() => {
  // Best effort first draw.
});
startDashboardAutoRefresh();
setFrameSummaryText("ожидание подключения камеры");
