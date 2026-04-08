using ASCOM;
using ASCOM.DeviceInterface;
using ASCOM.Utilities;
using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Runtime.InteropServices;

namespace ASCOM.ProjectR1
{
    [Guid("2D74A80F-31C2-4C01-8BDB-3C95F77EFD1A")]
    [ClassInterface(ClassInterfaceType.None)]
    public class Camera : ICameraV3
    {
        public const string DriverId = "ASCOM.ProjectR1.Camera";
        public const string DriverDescription = "GreatEyes 9.0 (Project_R1 ASCOM Camera)";

        /// <summary>SDK readout speed list (kHz); must match Python READOUT_SPEED_OPTIONS.</summary>
        public static readonly int[] ReadoutSpeedKhz = { 50, 100, 250, 500, 1000, 3000, 5000 };

        public static readonly string[] ReadoutModeLabels = { "50 kHz", "100 kHz", "250 kHz", "500 kHz", "1 MHz", "3 MHz", "5 MHz" };

        private readonly TraceLogger _tl;
        private readonly PythonApiClient _apiClient;

        private bool _connected;
        private bool _coolerOn;
        private double _setCcdTemp;
        private string _activeExposureId;
        private int _numX = 2048;
        private int _numY = 2052;
        private short _binX = 1;
        private short _binY = 1;
        private int _startX;
        private int _startY;
        private string _sensorName = "GreatEyes 9.0";
        private bool _hasShutter = true;
        private int _cameraXSize = 2048;
        private int _cameraYSize = 2052;
        private double _lastExposureDuration;
        private DateTime _lastExposureStart = DateTime.MinValue;

        public Camera()
        {
            _tl = new TraceLogger("", "ProjectR1.Camera");
            _tl.Enabled = true;
            _apiClient = new PythonApiClient();
        }

        public void SetupDialog()
        {
            using (var form = new CameraSetupForm(_apiClient))
            {
                form.ShowDialog();
            }
        }

        public ArrayList SupportedActions => new ArrayList { "ProjectR1:WarmUp" };

        public string Action(string actionName, string actionParameters)
        {
            if (string.Equals(actionName, "ProjectR1:WarmUp", StringComparison.OrdinalIgnoreCase))
            {
                CheckConnected(nameof(Action));
                _apiClient.PostJson("/camera/cooling/warmup", new
                {
                    target_temp_c = 0,
                    temp_step_c = 5,
                    power_step_percent = 10,
                    step_interval_sec = 30.0
                });
                return string.Empty;
            }
            throw new MethodNotImplementedException($"Action {actionName} is not implemented");
        }

        public void CommandBlind(string command, bool raw) => throw new MethodNotImplementedException(nameof(CommandBlind));
        public bool CommandBool(string command, bool raw) => throw new MethodNotImplementedException(nameof(CommandBool));
        public string CommandString(string command, bool raw) => throw new MethodNotImplementedException(nameof(CommandString));

        public void Dispose()
        {
            _tl.Enabled = false;
            _tl.Dispose();
        }

        public bool Connected
        {
            get => _connected;
            set
            {
                if (value == _connected) return;
                if (value)
                {
                    var response = _apiClient.PostJson("/camera/connect");
                    _connected = CameraApiValueReader.ReadBool(response, "connected");
                    RefreshCapabilities();
                    RefreshCoolingFromServer();
                }
                else
                {
                    _apiClient.PostJson("/camera/disconnect");
                    _connected = false;
                    _activeExposureId = null;
                }
            }
        }

        public string Description => DriverDescription;

        public string DriverInfo => "Project_R1 ASCOM proxy to Python service";

        public string DriverVersion => "0.2";

        public short InterfaceVersion => 3;

        public string Name => "GreatEyes 9.0";

        public void AbortExposure()
        {
            CheckConnected(nameof(AbortExposure));
            if (!string.IsNullOrEmpty(_activeExposureId))
            {
                try
                {
                    _apiClient.PostJson($"/camera/exposures/{_activeExposureId}/abort");
                }
                catch
                {
                    // Exposure may already be finished and removed from active path.
                }
            }
        }

        public short BayerOffsetX => throw new PropertyNotImplementedException(nameof(BayerOffsetX), false);
        public short BayerOffsetY => throw new PropertyNotImplementedException(nameof(BayerOffsetY), false);

        public short BinX
        {
            get => _binX;
            set
            {
                ValidateRoiBinning(value, _binY, _numX, _numY, _startX, _startY);
                _binX = value;
                PushRoiBinning();
            }
        }

        public short BinY
        {
            get => _binY;
            set
            {
                ValidateRoiBinning(_binX, value, _numX, _numY, _startX, _startY);
                _binY = value;
                PushRoiBinning();
            }
        }

        public double CCDTemperature
        {
            get
            {
                CheckConnected(nameof(CCDTemperature));
                var response = _apiClient.GetJson("/camera/cooling/status");
                return CameraApiValueReader.ReadDouble(response, "ccd_temp_c");
            }
        }

        public CameraStates CameraState
        {
            get
            {
                CheckConnected(nameof(CameraState));
                var response = _apiClient.GetJson("/camera/state");
                var state = CameraApiValueReader.ReadString(response, "camera_state");
                switch (state)
                {
                    case "idle": return CameraStates.cameraIdle;
                    case "exposing": return CameraStates.cameraExposing;
                    case "reading": return CameraStates.cameraReading;
                    case "error": return CameraStates.cameraError;
                    default: return CameraStates.cameraIdle;
                }
            }
        }

        public int CameraXSize => _cameraXSize;
        public int CameraYSize => _cameraYSize;
        public bool CanAbortExposure => true;
        public bool CanAsymmetricBin => true;
        public bool CanFastReadout => false;
        public bool CanGetCoolerPower => true;
        public bool CanPulseGuide => false;
        public bool CanSetCCDTemperature => true;
        public bool CanStopExposure => true;

        public bool CoolerOn
        {
            get
            {
                CheckConnected(nameof(CoolerOn));
                var response = _apiClient.GetJson("/camera/cooling/status");
                _coolerOn = CameraApiValueReader.ReadBool(response, "cooler_on");
                _tl.LogMessage(nameof(CoolerOn), $"GET cooler_on={_coolerOn.ToString(CultureInfo.InvariantCulture)}");
                return _coolerOn;
            }
            set
            {
                CheckConnected(nameof(CoolerOn));
                _tl.LogMessage(nameof(CoolerOn), $"SET requested={value.ToString(CultureInfo.InvariantCulture)}");
                Dictionary<string, object> response;
                if (value)
                {
                    response = _apiClient.PutJson("/camera/cooling/power", new { cooler_on = true });
                }
                else
                {
                    response = _apiClient.PutJson("/camera/cooling/power", new { cooler_on = false, cooler_power_percent = 0 });
                }
                _coolerOn = CameraApiValueReader.ReadBool(response, "cooler_on");
                _tl.LogMessage(nameof(CoolerOn), $"SET result cooler_on={_coolerOn.ToString(CultureInfo.InvariantCulture)}");
            }
        }

        public double CoolerPower
        {
            get
            {
                CheckConnected(nameof(CoolerPower));
                var response = _apiClient.GetJson("/camera/cooling/status");
                return CameraApiValueReader.ReadDouble(response, "cooler_power_percent");
            }
        }

        public double ElectronsPerADU => 1.0;
        public double ExposureMax => 3600.0;
        public double ExposureMin => 0.05;
        public double ExposureResolution => 0.01;
        public bool FastReadout { get => false; set => throw new PropertyNotImplementedException(nameof(FastReadout), true); }
        public double FullWellCapacity => throw new PropertyNotImplementedException(nameof(FullWellCapacity), false);
        public short Gain
        {
            get
            {
                try
                {
                    var st = _apiClient.GetJson("/settings");
                    var mode = CameraApiValueReader.ReadString(st, "default_gain_mode");
                    return mode == "0" ? (short)0 : (short)1;
                }
                catch
                {
                    return 1;
                }
            }
            set
            {
                CheckConnected(nameof(Gain));
                if (value < 0 || value > 1)
                {
                    throw new InvalidValueException(nameof(Gain), value.ToString(CultureInfo.InvariantCulture), "range 0..1");
                }
                _apiClient.PutJson("/settings", new { default_gain_mode = value.ToString(CultureInfo.InvariantCulture) });
            }
        }

        public short GainMax => 1;

        public short GainMin => 0;

        public ArrayList Gains => new ArrayList { "High capacity (SDK 0)", "Low noise (SDK 1)" };
        public bool HasShutter => _hasShutter;
        public double HeatSinkTemperature => throw new PropertyNotImplementedException(nameof(HeatSinkTemperature), false);

        public object ImageArray
        {
            get
            {
                CheckConnected(nameof(ImageArray));
                var binary = _apiClient.GetBinary("/camera/images/latest/raw");
                if (!binary.Headers.TryGetValue("X-Width", out var widthRaw) || !binary.Headers.TryGetValue("X-Height", out var heightRaw))
                {
                    throw new DriverException("ImageArray raw transfer failed: missing X-Width/X-Height headers");
                }

                var width = int.Parse(widthRaw, CultureInfo.InvariantCulture);
                var height = int.Parse(heightRaw, CultureInfo.InvariantCulture);
                var raw = binary.Data;
                var expectedLength = width * height * 2;
                if (raw.Length < expectedLength)
                {
                    throw new DriverException($"ImageArray raw transfer failed: expected {expectedLength} bytes, got {raw.Length}");
                }

                var image = new int[width, height];
                var byteOffset = 0;
                for (var y = 0; y < height; y++)
                {
                    for (var x = 0; x < width; x++)
                    {
                        image[x, y] = BitConverter.ToUInt16(raw, byteOffset);
                        byteOffset += 2;
                    }
                }
                return image;
            }
        }

        public object ImageArrayVariant => ImageArray;

        public bool ImageReady
        {
            get
            {
                CheckConnected(nameof(ImageReady));
                if (string.IsNullOrEmpty(_activeExposureId)) return false;
                var status = _apiClient.GetJson($"/camera/exposures/{_activeExposureId}/status");
                return CameraApiValueReader.ReadBool(status, "image_ready");
            }
        }

        public bool IsPulseGuiding => false;

        public double LastExposureDuration => _lastExposureDuration;

        public string LastExposureStartTime => _lastExposureStart == DateTime.MinValue
            ? string.Empty
            : _lastExposureStart.ToString("yyyy-MM-ddTHH:mm:ss", CultureInfo.InvariantCulture);

        public int MaxADU => 65535;
        public short MaxBinX => 4;
        public short MaxBinY => 4;

        public int NumX
        {
            get => _numX;
            set
            {
                ValidateRoiBinning(_binX, _binY, value, _numY, _startX, _startY);
                _numX = value;
                PushRoiBinning();
            }
        }

        public int NumY
        {
            get => _numY;
            set
            {
                ValidateRoiBinning(_binX, _binY, _numX, value, _startX, _startY);
                _numY = value;
                PushRoiBinning();
            }
        }

        public int Offset { get => throw new PropertyNotImplementedException(nameof(Offset), false); set => throw new PropertyNotImplementedException(nameof(Offset), true); }
        public int OffsetMax => throw new PropertyNotImplementedException(nameof(OffsetMax), false);
        public int OffsetMin => throw new PropertyNotImplementedException(nameof(OffsetMin), false);
        public ArrayList Offsets => throw new PropertyNotImplementedException(nameof(Offsets), false);
        public short PercentCompleted => throw new PropertyNotImplementedException(nameof(PercentCompleted), false);
        public double PixelSizeX => 13.0;
        public double PixelSizeY => 13.0;
        public void PulseGuide(GuideDirections Direction, int Duration) => throw new MethodNotImplementedException(nameof(PulseGuide));
        public short ReadoutMode
        {
            get
            {
                try
                {
                    var st = _apiClient.GetJson("/settings");
                    var speed = CameraApiValueReader.ReadInt(st, "readout_speed");
                    for (short i = 0; i < ReadoutSpeedKhz.Length; i++)
                    {
                        if (ReadoutSpeedKhz[i] == speed)
                        {
                            return i;
                        }
                    }
                    return 0;
                }
                catch
                {
                    return 0;
                }
            }
            set
            {
                if (value < 0 || value >= ReadoutSpeedKhz.Length)
                {
                    throw new InvalidValueException(
                        nameof(ReadoutMode),
                        value.ToString(CultureInfo.InvariantCulture),
                        $"range 0..{ReadoutSpeedKhz.Length - 1}");
                }
                _apiClient.PutJson("/settings", new { readout_speed = ReadoutSpeedKhz[value] });
            }
        }

        public ArrayList ReadoutModes
        {
            get
            {
                var list = new ArrayList();
                foreach (var label in ReadoutModeLabels)
                {
                    list.Add(label);
                }
                return list;
            }
        }
        public string SensorName => _sensorName;
        public SensorType SensorType => SensorType.Monochrome;

        public double SetCCDTemperature
        {
            get
            {
                CheckConnected(nameof(SetCCDTemperature));
                var response = _apiClient.GetJson("/camera/cooling/status");
                _setCcdTemp = CameraApiValueReader.ReadDouble(response, "target_temp_c");
                _tl.LogMessage(nameof(SetCCDTemperature), $"GET target_temp_c={_setCcdTemp.ToString(CultureInfo.InvariantCulture)}");
                return _setCcdTemp;
            }
            set
            {
                CheckConnected(nameof(SetCCDTemperature));
                var rounded = (int)Math.Round(value);
                _tl.LogMessage(nameof(SetCCDTemperature), $"SET requested={value.ToString(CultureInfo.InvariantCulture)} rounded={rounded.ToString(CultureInfo.InvariantCulture)}");
                var response = _apiClient.PutJson("/camera/cooling/target", new { target_temp_c = rounded });
                _setCcdTemp = CameraApiValueReader.ReadDouble(response, "target_temp_c");
                _tl.LogMessage(nameof(SetCCDTemperature), $"SET result target_temp_c={_setCcdTemp.ToString(CultureInfo.InvariantCulture)}");
            }
        }

        public void StartExposure(double Duration, bool Light)
        {
            CheckConnected(nameof(StartExposure));
            _lastExposureDuration = Duration;
            _lastExposureStart = DateTime.Now;
            var response = _apiClient.PostJson("/camera/exposures", new { duration_sec = Duration, light = Light });
            _activeExposureId = CameraApiValueReader.ReadString(response, "exposure_id");
        }

        public int StartX
        {
            get => _startX;
            set
            {
                ValidateRoiBinning(_binX, _binY, _numX, _numY, value, _startY);
                _startX = value;
                PushRoiBinning();
            }
        }

        public int StartY
        {
            get => _startY;
            set
            {
                ValidateRoiBinning(_binX, _binY, _numX, _numY, _startX, value);
                _startY = value;
                PushRoiBinning();
            }
        }

        public void StopExposure()
        {
            CheckConnected(nameof(StopExposure));
            if (!string.IsNullOrEmpty(_activeExposureId))
            {
                try
                {
                    _apiClient.PostJson($"/camera/exposures/{_activeExposureId}/stop");
                }
                catch
                {
                    // Exposure may already be finished and removed from active path.
                }
            }
        }

        public double SubExposureDuration
        {
            get => throw new PropertyNotImplementedException(nameof(SubExposureDuration), false);
            set => throw new PropertyNotImplementedException(nameof(SubExposureDuration), true);
        }

        [ComRegisterFunction]
        public static void RegisterASCOM(Type t)
        {
            using (var profile = new Profile())
            {
                profile.DeviceType = "Camera";
                profile.Register(DriverId, DriverDescription);
            }
        }

        [ComUnregisterFunction]
        public static void UnregisterASCOM(Type t)
        {
            using (var profile = new Profile())
            {
                profile.DeviceType = "Camera";
                profile.Unregister(DriverId);
            }
        }

        private void RefreshCoolingFromServer()
        {
            if (!_connected)
            {
                return;
            }
            try
            {
                var response = _apiClient.GetJson("/camera/cooling/status");
                _coolerOn = CameraApiValueReader.ReadBool(response, "cooler_on");
                _setCcdTemp = CameraApiValueReader.ReadDouble(response, "target_temp_c");
            }
            catch
            {
            }
        }

        private void RefreshCapabilities()
        {
            var capabilities = _apiClient.GetJson("/camera/capabilities");
            _cameraXSize = CameraApiValueReader.ReadInt(capabilities, "camera_x_size");
            _cameraYSize = CameraApiValueReader.ReadInt(capabilities, "camera_y_size");
            _sensorName = CameraApiValueReader.ReadString(capabilities, "sensor_name");
            _hasShutter = CameraApiValueReader.ReadBool(capabilities, "has_shutter");
            _numX = _cameraXSize;
            _numY = _cameraYSize;
        }

        private void PushRoiBinning()
        {
            if (!_connected) return;
            _apiClient.PutJson("/camera/config/roi-binning", new
            {
                bin_x = _binX,
                bin_y = _binY,
                num_x = _numX,
                num_y = _numY,
                start_x = _startX,
                start_y = _startY
            });
        }

        private void ValidateRoiBinning(short binX, short binY, int numX, int numY, int startX, int startY)
        {
            if (binX < 1 || binX > MaxBinX) throw new InvalidValueException(nameof(BinX), binX.ToString(), $"range 1..{MaxBinX}");
            if (binY < 1 || binY > MaxBinY) throw new InvalidValueException(nameof(BinY), binY.ToString(), $"range 1..{MaxBinY}");
            if (numX < 1 || numX > _cameraXSize) throw new InvalidValueException(nameof(NumX), numX.ToString(), $"range 1..{_cameraXSize}");
            if (numY < 1 || numY > _cameraYSize) throw new InvalidValueException(nameof(NumY), numY.ToString(), $"range 1..{_cameraYSize}");
            if (startX < 0 || startX >= _cameraXSize) throw new InvalidValueException(nameof(StartX), startX.ToString(), $"range 0..{_cameraXSize - 1}");
            if (startY < 0 || startY >= _cameraYSize) throw new InvalidValueException(nameof(StartY), startY.ToString(), $"range 0..{_cameraYSize - 1}");
            if (startX + numX > _cameraXSize) throw new InvalidValueException(nameof(NumX), numX.ToString(), "StartX + NumX exceeds CameraXSize");
            if (startY + numY > _cameraYSize) throw new InvalidValueException(nameof(NumY), numY.ToString(), "StartY + NumY exceeds CameraYSize");
        }

        private void CheckConnected(string member)
        {
            if (!_connected) throw new NotConnectedException(member);
        }

    }
}
