try {
    $cam = New-Object -ComObject ASCOM.ProjectR1.Camera
    "COM32_OK=True"
    $cam.Connected = $true
    "CONNECTED=$($cam.Connected)"

    "CAMERA_STATE=$($cam.CameraState)"
    "CAMERA_X_SIZE=$($cam.CameraXSize)"
    "CAMERA_Y_SIZE=$($cam.CameraYSize)"
    "SENSOR_NAME=$($cam.SensorName)"
    "HAS_SHUTTER=$($cam.HasShutter)"
    "CAN_ABORT=$($cam.CanAbortExposure)"
    "CAN_STOP=$($cam.CanStopExposure)"
    "CAN_SET_TEMP=$($cam.CanSetCCDTemperature)"

    $cam.BinX = 1
    $cam.BinY = 1
    $cam.NumX = 1024
    $cam.NumY = 1026
    $cam.StartX = 0
    $cam.StartY = 0
    "ROI_BINNING_SET=OK"

    $cam.CoolerOn = $true
    "COOLER_ON=$($cam.CoolerOn)"
    $cam.SetCCDTemperature = -15
    Start-Sleep -Milliseconds 700
    "CCD_TEMP_AFTER_SET=$($cam.CCDTemperature)"
    "COOLER_POWER_AFTER_SET=$($cam.CoolerPower)"

    $cam.StartExposure(1.2, $false)
    Start-Sleep -Milliseconds 300
    $cam.AbortExposure()
    "ABORT_DURING_EXPOSURE=OK"

    $cam.StartExposure(1.2, $false)
    Start-Sleep -Milliseconds 300
    $cam.StopExposure()
    "STOP_DURING_EXPOSURE=OK"

    $cam.CoolerOn = $false
    "COOLER_OFF=$($cam.CoolerOn)"

    $cam.Connected = $false
    "DISCONNECTED=$($cam.Connected)"
}
catch {
    "COM32_EXTENDED_ERR=$($_.Exception.Message)"
}
