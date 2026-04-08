try {
    $cam = New-Object -ComObject ASCOM.ProjectR1.Camera
    "COM32_OK=True"
    $cam.Connected = $true
    "CONNECTED=$($cam.Connected)"

    $cam.StartExposure(0.3, $false)
    $ready = $false
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Milliseconds 500
        if ($cam.ImageReady) {
            $ready = $true
            break
        }
    }
    "IMAGE_READY=$ready"

    if ($ready) {
        $img = $cam.ImageArray
        "IMAGE_ARRAY_TYPE=$($img.GetType().FullName)"
        "IMAGE_ARRAY_LEN=$($img.Length)"
        "IMAGE_PIXEL_0_0=$($img.GetValue(0,0))"
    }
    else {
        "IMAGE_ARRAY_SKIPPED=not_ready"
    }

    try { "CCD_TEMP=$($cam.CCDTemperature)" } catch { "CCD_TEMP_ERR=$($_.Exception.Message)" }
    try { "COOLER_POWER=$($cam.CoolerPower)" } catch { "COOLER_POWER_ERR=$($_.Exception.Message)" }

    try { $cam.AbortExposure(); "ABORT_OK=True" } catch { "ABORT_ERR=$($_.Exception.Message)" }
    try { $cam.StopExposure(); "STOP_OK=True" } catch { "STOP_ERR=$($_.Exception.Message)" }
    $cam.Connected = $false
    "DISCONNECTED=$($cam.Connected)"
}
catch {
    "COM32_SMOKE_ERR=$($_.Exception.Message)"
}
