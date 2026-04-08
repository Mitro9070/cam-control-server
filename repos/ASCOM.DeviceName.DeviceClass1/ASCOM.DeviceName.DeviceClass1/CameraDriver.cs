//tabs=4
// --------------------------------------------------------------------------------
// TODO fill in this information for your driver, then remove this line!
//
// ASCOM Camera driver for MyFunkyCamera
//
// Description:	Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam 
//				nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam 
//				erat, sed diam voluptua. At vero eos et accusam et justo duo 
//				dolores et ea rebum. Stet clita kasd gubergren, no sea takimata 
//				sanctus est Lorem ipsum dolor sit amet.
//
// Implements:	ASCOM Camera interface version: <To be completed by driver developer>
// Author:		(XXX) Your N. Here <your@email.here>
//
// Edit Log:
//
// Date			Who	Vers	Description
// -----------	---	-----	-------------------------------------------------------
// dd-mmm-yyyy	XXX	6.0.0	Initial edit, created from ASCOM driver template
// --------------------------------------------------------------------------------
//


// This is used to define code in the template that is specific to one class implementation
// unused code can be deleted and this definition removed.
#define Camera

using ASCOM;
using ASCOM.Astrometry;
//using ASCOM.Astrometry.AstroUtils;
using ASCOM.DeviceInterface;
using ASCOM.Utilities;
using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.Runtime.InteropServices;
using System.Text;

namespace ASCOM.MyFunkyCamera
{
    /*
     Your driver's DeviceID is ASCOM.MyFunkyCamera.Camera
    
     The Guid attribute sets the CLSID for ASCOM.MyFunkyCamera.Camera
     The ClassInterface/None attribute prevents an empty interface called
     _MyFunkyCamera from being created and used as the [default] interface
    
     TODO Replace the not implemented exceptions with code to implement the function or
     throw the appropriate ASCOM exception.
    
    */
    /// <summary>
    /// ASCOM Camera Driver for GreatEye 2048 camera.
    /// </summary>
    [Guid("866bdb80-2462-4d93-817b-56dd70bbfe6c")]
    [ClassInterface(ClassInterfaceType.None)]
    public class Camera : ICameraV3
    {
        /// <summary>
        /// ASCOM DeviceID (COM ProgID) for this driver.
        /// The DeviceID is used by ASCOM applications to load the driver at runtime.
        /// </summary>
        public const string driverID = "ASCOM.MyFunkyCamera.Camera";
        // TODO Change the descriptive string for your driver then remove this line
        /// <summary>
        /// Driver description that displays in the ASCOM Chooser.
        /// </summary>
        public const string driverDescription = "My Funky driver for GE2048 camera";

        //internal static string comPortProfileName = "COM Port"; // Constants used for Profile persistence
        //internal static string gainProfileName = "Gain"; // Constants used for Profile persistence

        //internal static string comPortDefault = "COM1";
        internal static string gainDefault = "1";

        //   internal static string traceStateProfileName = "Trace Level";
        //   internal static string traceStateDefault = "false";

        /// <summary>
        /// Private variable to hold the connected state
        /// </summary>
        private bool connectedState;
        /// <summary>
        /// Private variable to hold an ASCOM Utilities object
        /// </summary>
        private Util utilities;

        /// <summary>
        /// Private variable to hold an ASCOM AstroUtilities object to provide the Range method
        /// </summary>
        //private AstroUtils astroUtilities;

        /// <summary>
        /// Variable to hold the trace logger object (creates a diagnostic log file with information that you specify)
        /// </summary>
        internal TraceLogger tl;

        /// <summary>
        /// Initializes a new instance of the <see cref="MyFunkyCamera"/> class.
        /// Must be public for COM registration.
        /// </summary>

        #region ge2048_link
        #region DLL_import
        //const string nativeDLLname = "SimplestNativeDLL.dll";
        const string nativeDLLname = "greateyes.dll";

        [DllImport(nativeDLLname, ExactSpelling = false, CallingConvention = CallingConvention.Cdecl, SetLastError = true)]
        private static extern bool ConnectCamera(out int modelId, out IntPtr ptrToModelStr, out int statusMSG, int addr);

        [DllImport(nativeDLLname, CallingConvention = CallingConvention.Cdecl)]
        private static extern bool DisconnectCamera(out int statusMSG, int addr);

        [DllImport(nativeDLLname, CallingConvention = CallingConvention.Cdecl)]
        private static extern int GetNumberOfConnectedCams();

        [DllImport(nativeDLLname, CallingConvention = CallingConvention.Cdecl)]
        private static extern bool CloseCamera(int address, bool JustShootEm);

        [DllImport(nativeDLLname, CallingConvention = CallingConvention.Cdecl)]
        private static extern int GetMaxExposureTime(int addr);

        #region temperature_control
        [DllImport(nativeDLLname, CallingConvention = CallingConvention.Cdecl)]
        private static extern int TemperatureControl_Setup(int coolingHardware, out int statusMSG, int addr); // coolingHardware = 42223

        [DllImport(nativeDLLname, CallingConvention = CallingConvention.Cdecl)]
        private static extern string TemperatureControl_GetLevelString(int index, out int statusMSG, int addr);

        [DllImport(nativeDLLname, CallingConvention = CallingConvention.Cdecl)]
        private static extern bool TemperatureControl_SetTemperatureLevel(int ge2048_coolerLevel, out int statusMSG, int addr);

        [DllImport(nativeDLLname, CallingConvention = CallingConvention.Cdecl)]
        private static extern bool TemperatureControl_SetTemperature(int temperature, out int statusMSG, int addr);

        [DllImport(nativeDLLname, CallingConvention = CallingConvention.Cdecl)]
        private static extern bool TemperatureControl_GetTemperature(int thermistor, out int temperature, out int statusMSG, int addr);

        [DllImport(nativeDLLname, CallingConvention = CallingConvention.Cdecl)]
        private static extern bool TemperatureControl_SwitchOff(out int statusMSG, int addr);
        #endregion

        [DllImport(nativeDLLname, CallingConvention = CallingConvention.Cdecl)]
        private static extern bool StartMeasurement(bool CorrectBias, bool showSync, bool showShutter, bool triggerMode, int triggerTimeOut, out int statusMSG, int addr);

        [DllImport(nativeDLLname, CallingConvention = CallingConvention.Cdecl)]
        private static extern bool PerformMeasurement_Blocking(bool CorrectBias, bool showSync, bool showShutter, bool triggerMode, int triggerTimeOut,
            ushort[] pInDataStart, out int writebytes, out int readBytes, out int statusMSG, int addr);

        [DllImport(nativeDLLname, CallingConvention = CallingConvention.Cdecl)]
        private static extern bool GetMeasurementData(ushort[] pInDataStart, out int writebytes, out int readBytes, out int statusMSG, int addr);

        [DllImport(nativeDLLname, CallingConvention = CallingConvention.Cdecl)]
        private static extern bool CamSettings(int readoutSpeed, int exposureTime_ms, int binningX, int binningY, out int numPixelInX, out int numPixelInY, out int pixelSize, out int statusMSG, int addr);

        [DllImport(nativeDLLname, CallingConvention = CallingConvention.Cdecl)]
        private static extern int GetMaxBinningX(out int statusMSG, int cameraAddress);

        [DllImport(nativeDLLname, CallingConvention = CallingConvention.Cdecl)]         
        private static extern int GetMaxBinningY(out int statusMSG, int cameraAddress);

        [DllImport(nativeDLLname, CallingConvention = CallingConvention.Cdecl)]
        private static extern bool StopMeasurement(int addr);

        [DllImport(nativeDLLname, CallingConvention = CallingConvention.Cdecl)]
        private static extern bool OpenShutter(int state, out int statusMSG, int addr);

        [DllImport(nativeDLLname, CallingConvention = CallingConvention.Cdecl)]
        private static extern bool SetupGain(int gainSeting, out int statusMSG, int addr);

        [DllImport(nativeDLLname, CallingConvention = CallingConvention.Cdecl)]
        private static extern bool DllIsBusy(int addr);

        [DllImport(nativeDLLname, CallingConvention = CallingConvention.Cdecl)]
        private static extern int ActivateCropMode(bool on, out int statusMSG, int addr);

        [DllImport(nativeDLLname, CallingConvention = CallingConvention.Cdecl)]
        private static extern bool SetupCropMode2D(int col, int line, out int statusMSG, int addr);

        #endregion

        #region ge2048_fields
        private static ushort[] pInDataStart;
        private static int modelId;
        private string modelStr;
        private int maxExposureTime_ms;
        private int numberOfCoolerLevels;
        private const int coolingHardware = 42223;
        private bool cameraCoolerState;
        private int cameraSetPointTemperature;
        private int ge2048_coolerLevel = 25; // 1..25 
        private double ge2048_exposureMin = 0.05; // sec
        private const int temperatureBackMax = 55;
        private int temperatureBack;
        private int temperatureCCD;        
        private CameraStates cameraStateCurrent;
        #endregion

        private System.Threading.Thread expositionThread;
        private System.Threading.Thread expositionAwaiter;
       
        public enum GE2048_Messages
        {
            MESSAGE_Camera_Ok = 0,                 // camera detected and ok
            MESSAGE_NoCamera_Connected = 1,        // no camera detected
            MESSAGE_could_not_open_USBDevice = 2,  // there is a problem with the USB interface
            MESSAGE_WriteConfigTable_Failed = 3,   // transferring data to cam failed - TimeOut!
            MESSAGE_WriteReadRequest_Failed = 4,   // receiving data from cam failed - TimeOut!
            MESSAGE_NoTrigger = 5,                 // no extern trigger signal within time window of TriggerTimeOut
            MESSAGE_NewCameraDetected = 6,         // new cam detected - you need to perform CamSettings
            MESSAGE_UnknownCamID = 7,              // this DLL was not written for connected cam - please request new greateyes.dll
            MESSAGE_OutofRange = 8,                // one ore more parameters are out of range
            Message_NoNewData = 9,                 // no new image data
            Message_Busy = 10,                     // camera busy
            Message_CoolingTurnedOff = 11,         // cooling turned off
            Message_MeasurementStopped = 12,       // measurement stopped
            Message_BurstModeTooMuchPixels = 13    // too many pixels for BurstMode. Set lower number of measurements or higher binning level
        };
 
        private static readonly Dictionary<GE2048_Messages, string> GE2048_messageDict = new Dictionary<GE2048_Messages, string>
        {
            { GE2048_Messages.MESSAGE_Camera_Ok,                 "camera detected and ok" },
            { GE2048_Messages.MESSAGE_NoCamera_Connected,        "no camera detected" },
            { GE2048_Messages.MESSAGE_could_not_open_USBDevice,  "there is a problem with the USB interface" },
            { GE2048_Messages.MESSAGE_WriteConfigTable_Failed,   "transferring data to cam failed - TimeOut!" },
            { GE2048_Messages.MESSAGE_WriteReadRequest_Failed,   "receiving data from cam failed - TimeOut!" },
            { GE2048_Messages.MESSAGE_NoTrigger,                 "no extern trigger signal within time window of TriggerTimeOut" },
            { GE2048_Messages.MESSAGE_NewCameraDetected,         "new cam detected - you need to perform CamSettings" },
            { GE2048_Messages.MESSAGE_UnknownCamID,              "this DLL was not written for connected cam - please request new greateyes.dll" },
            { GE2048_Messages.MESSAGE_OutofRange,                "one or more parameters are out of range" },
            { GE2048_Messages.Message_NoNewData,                 "no new image data" },
            { GE2048_Messages.Message_Busy,                      "camera busy" },
            { GE2048_Messages.Message_CoolingTurnedOff,          "cooling turned off" },
            { GE2048_Messages.Message_MeasurementStopped,        "measurement stopped" },
            { GE2048_Messages.Message_BurstModeTooMuchPixels,    "too many pixels for BurstMode. Set lower number of measurements or higher binning level" }
        };

        private static readonly Dictionary<string, int> GE2048_readoutSpeedDict = new Dictionary<string, int>
        {
            { "1000", 0 },
            { "2800", 3 },
            { "500",  5 }    
        };

        private static readonly Dictionary<string, int> GE2048_rawGain2codeDict = new Dictionary<string, int>
        {
            { "1", 1 },
            { "2", 0 }
        };

        private static readonly Dictionary<string, double> GE2048_rawGain2preciseDict = new Dictionary<string, double>
        {
            { "1", 1.0 },
            { "2", 2.0 }
        };

        #endregion

        public Camera()
        {
            tl = new TraceLogger("", "MyFunkyCamera");
            tl.Enabled = Properties.Settings.Default.TraceEnabled;  //  Convert.ToBoolean(driverProfile.GetValue(driverID, traceStateProfileName, string.Empty, traceStateDefault));
            // JK
            // string hhh = Properties.Settings.Default.CCDHeight;
            //   ReadProfile(); // Read device configuration from the ASCOM Profile store

            ge2048_coolerLevel = Convert.ToInt32(Properties.Settings.Default.CoolerLevel);          
            string defaultReadoutSpeed = "500";
            if (! GE2048_readoutSpeedDict.ContainsKey(Properties.Settings.Default.ReadoutSpeed)) {
                Properties.Settings.Default.ReadoutSpeed = defaultReadoutSpeed;
            }
            ge2048_readoutSpeed = GE2048_readoutSpeedDict[Properties.Settings.Default.ReadoutSpeed];

            tl.LogMessage("Camera", "Starting initialisation");  // In MAXIM DL Connect

            connectedState = false; // Initialise connected to false
            utilities = new Util(); //Initialise util object
                                    //astroUtilities = new AstroUtils(); // Initialise astro-utilities object
                                    //TODO: Implement your additional construction maxExhere
            #region ge2048            
            int numberOfCamsConnected = GetNumberOfConnectedCams();
            int statusMSG;
            for (int addr = 0; addr < numberOfCamsConnected; addr++)
            {
                bool res = DisconnectCamera(out statusMSG, addr);
                //CheckGE2048_status("Camera constructor", res, statusMSG);
            }
            cameraAddress = 0; // Check here ??!!!
            maxExposureTime_ms = GetMaxExposureTime(cameraAddress);

            /*int statusMSG;
            ge2048_binningXmax = GetMaxBinningX(out statusMSG, cameraAddress);    // Gives wrong value 4096 !!! Fix 2000 for full image // Do it after changing crop mode too !!!!!!!! JK TODO 
            ge2048_binningYmax = GetMaxBinningY(out statusMSG, cameraAddress);    // -"-           
            */
            #endregion            
            tl.LogMessage("Camera", "Completed initialisation"); // MAXIM DL Connect
        }

        //
        // PUBLIC COM INTERFACE ICameraV3 IMPLEMENTATION
        //

        #region Common properties and methods.

        /// <summary>
        /// Displays the Setup Dialog form.
        /// If the user clicks the OK button to dismiss the form, then
        /// the new settings are saved, otherwise the old values are reloaded.
        /// THIS IS THE ONLY PLACE WHERE SHOWING USER INTERFACE IS ALLOWED!
        /// </summary>
        public void SetupDialog()
        {
            // consider only showing the setup dialog if not connected
            // or call a different dialog if connected
            if (IsConnected)
                System.Windows.Forms.MessageBox.Show("Already connected, just press OK");

            using (SetupDialogForm F = new SetupDialogForm(tl))
            {
                var result = F.ShowDialog();
                if (result == System.Windows.Forms.DialogResult.OK)
                {
                    Properties.Settings.Default.Save();
             //       WriteProfile(); // Persist device configuration values to the ASCOM Profile store
                }
                else
                {
                    Properties.Settings.Default.Reload();
                }


            }
        }

        public ArrayList SupportedActions
        {
            get
            {
                tl.LogMessage("SupportedActions Get", "Returning empty arraylist");
                return new ArrayList();
            }
        }

        public string Action(string actionName, string actionParameters)
        {
            LogMessage("", "Action {0}, parameters {1} not implemented", actionName, actionParameters);
            throw new ASCOM.ActionNotImplementedException("Action " + actionName + " is not implemented by this driver");
        }

        public void CommandBlind(string command, bool raw)
        {
            CheckConnected("CommandBlind");
            // TODO The optional CommandBlind method should either be implemented OR throw a MethodNotImplementedException
            // If implemented, CommandBlind must send the supplied command to the mount and return immediately without waiting for a response

            throw new ASCOM.MethodNotImplementedException("CommandBlind");
        }

        public bool CommandBool(string command, bool raw)
        {
            CheckConnected("CommandBool");
            // TODO The optional CommandBool method should either be implemented OR throw a MethodNotImplementedException
            // If implemented, CommandBool must send the supplied command to the mount, wait for a response and parse this to return a True or False value

            // string retString = CommandString(command, raw); // Send the command and wait for the response
            // bool retBool = XXXXXXXXXXXXX; // Parse the returned string and create a boolean True / False value
            // return retBool; // Return the boolean value to the client

            throw new ASCOM.MethodNotImplementedException("CommandBool");
        }

        public string CommandString(string command, bool raw)
        {
            CheckConnected("CommandString");
            // TODO The optional CommandString method should either be implemented OR throw a MethodNotImplementedException
            // If implemented, CommandString must send the supplied command to the mount and wait for a response before returning this to the client

            throw new ASCOM.MethodNotImplementedException("CommandString");
        }

        public void Dispose()
        {
            // Clean up the trace logger and util objects
            tl.Enabled = false;
            tl.Dispose();
            tl = null;
            utilities.Dispose();
            utilities = null;
            //astroUtilities.Dispose();
            //astroUtilities = null;
        }

        public bool Connected
        {
            get
            {
                LogMessage("Connected", "Get {0}", IsConnected);
                return IsConnected;
            }
            set
            {
                tl.LogMessage("Connected", "Set value to");
                tl.LogMessage("Connected set", Convert.ToString(value));
                if (value == IsConnected)
                    return;

                if (value)
                {
                    connectedState = true;                    
                    LogMessage("Connected Set", "camera\'s gain is {0}", Properties.Settings.Default.GainName); // GainName is raw gain in e-/ADU
                    
                    IntPtr ptrToModelStr = new IntPtr(0);
                    bool res = ConnectCamera(out modelId, out ptrToModelStr, out int statusMSG, cameraAddress);
                    CheckGE2048_status("ConnectCamera", res, statusMSG);
                    modelStr = Marshal.PtrToStringAnsi(ptrToModelStr);
                    LogMessage("ConnectCamera", "modelId = {0} modelStr = {1}", modelId, modelStr);

                    int exposureTime_ms = 1000; // to init camera only
                    int binX = 1;               // to init camera only
                    int binY = 1;               // to init camera only

                    res = CamSettings(ge2048_readoutSpeed, exposureTime_ms, binX, binY, out cameraNumX, out cameraNumY, out int ge2048_pixelSize, out statusMSG, cameraAddress);
                    CheckGE2048_status("Connect camera", res, statusMSG);
                    // pixelSize = ge2048_pixelSize;   // cast int to double< yes, this is INT size of pixel GE2048 !!!
                    LogMessage("Connect settings 1", "pixel size = {0} cameraNumX = {1} cameraNumY = {2}", pixelSize, cameraNumX, cameraNumY);


                    int resInt = ActivateCropMode(true, out statusMSG, cameraAddress);
                    res = SetupCropMode2D(ccdWidth, ccdHeight, out statusMSG, cameraAddress);
                    LogMessage("Activate Crop Mode", "resInt = {0} res = {1}", resInt, res);
                    CheckGE2048_status("SetupCropMode", res, statusMSG);

                    res = CamSettings(ge2048_readoutSpeed, exposureTime_ms, binX, binY, out cameraNumX, out cameraNumY, out ge2048_pixelSize, out statusMSG, cameraAddress);
                    CheckGE2048_status("Connect camera", res, statusMSG);
                    // pixelSize = ge2048_pixelSize;   // cast int to double< yes, this is INT size of pixel GE2048 !!!
                    LogMessage("Connect settings 2", "pixel size = {0} cameraNumX = {1} cameraNumY = {2}", pixelSize, cameraNumX, cameraNumY);
                    numberOfCoolerLevels = TemperatureControl_Setup(coolingHardware, out statusMSG, cameraAddress);
                    CheckGE2048_status("TemperatureControl_Setup", res, statusMSG);

                    if (!GE2048_rawGain2codeDict.ContainsKey(Properties.Settings.Default.GainName))
                    {
                        Properties.Settings.Default.GainName = gainDefault;
                    }
                    int gain = GE2048_rawGain2codeDict[Properties.Settings.Default.GainName];
                    res = SetupGain(gain, out statusMSG, cameraAddress);
                    CheckGE2048_status("SetupGain", res, statusMSG);
                    cameraStateCurrent = CameraStates.cameraIdle;
                }
                else
                {
                    connectedState = false;
                    // LogMessage("Connected Set", "Disconnecting from port {0}", comPort);
                    LogMessage("Connected Set", "Disconnected");

                    // TODO disconnect from the device
                    bool res = DisconnectCamera(out int statusMSG, cameraAddress);
                    CheckGE2048_status("DisonnectCamera", res, statusMSG);
                }
            }
        }

        public string Description
        {
            get
            {
                tl.LogMessage("Description Get", driverDescription);
                return modelStr + " model " + modelId.ToString();
            }
        }

        public string DriverInfo
        {
            get
            {
                Version version = System.Reflection.Assembly.GetExecutingAssembly().GetName().Version;
                // TODO customise this driver description
                string driverInfo = "Information about the driver itself. Version: " + String.Format(CultureInfo.InvariantCulture, "{0}.{1}", version.Major, version.Minor);
                tl.LogMessage("DriverInfo Get", driverInfo);
                return driverInfo;
            }
        }

        public string DriverVersion
        {
            get
            {
                Version version = System.Reflection.Assembly.GetExecutingAssembly().GetName().Version;
                string driverVersion = String.Format(CultureInfo.InvariantCulture, "{0}.{1}", version.Major, version.Minor);
                tl.LogMessage("DriverVersion Get", driverVersion);
                return driverVersion;
            }
        }

        public short InterfaceVersion
        {
            // set by the driver wizard
            get
            {
                LogMessage("InterfaceVersion Get", "3");
                return Convert.ToInt16("3");
            }
        }

        public string Name
        {
            get
            {
                string name = "FunkyCamera";
                tl.LogMessage("Name Get", name);
                return name;
            }
        }

        #endregion

        #region ICamera Implementation

        private const int ccdWidth = 2048; // Constants to define the CCD pixel dimensions
        private const int ccdHeight = 2052; // JK 1040;
        private const double pixelSize = 13.5; // Constant for the pixel physical dimension

        private int cameraNumX = ccdWidth; // Initialise variables to hold values required for functionality tested by Conform
        private int cameraNumY = ccdHeight;
        private int cameraStartX = 0;       // GE2048 can't change that
        private int cameraStartY = 0;       // -"-
        private DateTime exposureStart = DateTime.MinValue;
        private double cameraLastExposureDuration = 0.0;
        private static bool cameraImageReady = false;
        private int[,] cameraImageArray;
        private object[,] cameraImageArrayVariant;
        #region ge2048
        private int cameraAddress = 0;
        private short cameraXbin = 1;
        private short cameraYbin = 1;
        private const int ge2048_binningXmax = 4;   // Valid for the full image only.  Get it from GetMaxBinning (gives wrong value!)
        private const int ge2048_binningYmax = 4;   // Get it from GetMaxBinning! No!
        /* private List<short> validBinXlist;
        private string validBinXstring;
        private string validBinYstring;
        private List<short> validBinYlist;
        */
        private int ge2048_readoutSpeed = 5; // m.b. 0 - 1MHz, 3 - 3MHz, 5 - 500 kHz(!), 6 - 50 kHz(!) Yes!
        //private static int countTmp = 0;  // TMP counter Remove it JK TMP !!!
        #endregion


        public void AbortExposure()
        {
            tl.LogMessage("AbortExposure", "Not implemented");
            throw new MethodNotImplementedException("AbortExposure");
        }

        public short BayerOffsetX
        {
            get
            {
                tl.LogMessage("BayerOffsetX Get", "Not implemented");
                throw new ASCOM.PropertyNotImplementedException("BayerOffsetX", false);
            }
        }

        public short BayerOffsetY
        {
            get
            {
                tl.LogMessage("BayerOffsetY Get", "Not implemented");
                throw new ASCOM.PropertyNotImplementedException("BayerOffsetX", true);
            }
        }

        public short BinX
        {
            get
            {
                CheckConnected("Get BinY");
                tl.LogMessage("BinX Get", cameraXbin.ToString());
                return cameraXbin;
            }
            set       // Affect on NumPix
            {
                tl.LogMessage("BinX Set", value.ToString());
                if (value > ge2048_binningXmax)
                {
                    tl.LogMessage("Set BinX", "Invalid value " + Convert.ToString(value) + " > " + Convert.ToString(ge2048_binningXmax));
                    throw new ASCOM.InvalidValueException("BinX", value.ToString(), " <= " + ge2048_binningXmax.ToString());
                }
                cameraXbin = value;
            }
        }

        public short BinY
        {
            get
            {
                CheckConnected("Get BinY");
                tl.LogMessage("BinY Get", cameraYbin.ToString());
                return cameraYbin;
            }
            set
            {
                tl.LogMessage("BinY Set", value.ToString());
                if (value > ge2048_binningYmax)
                {
                    tl.LogMessage("Set BinY", "Invalid value " + Convert.ToString(value) + " > " + Convert.ToString(ge2048_binningYmax));
                    throw new ASCOM.InvalidValueException("BinY", value.ToString(), " <= " + ge2048_binningYmax.ToString());
                }
                cameraYbin = value;
            }
        }

        public double CCDTemperature // JK Ok
        {
            get
            {
                if (cameraStateCurrent != CameraStates.cameraIdle)
                {
                    return temperatureCCD;      // forbid temperature checking during exosition
                }
                
                int thermistor = 0; // CCD temperature
                bool res = TemperatureControl_GetTemperature(thermistor, out temperatureCCD, out int statusMSG, cameraAddress);
                CheckGE2048_status("GetTemperature CCD", res, statusMSG);

                thermistor = 1; // TEC backside temperature (Check it periodically)             
                res = TemperatureControl_GetTemperature(thermistor, out temperatureBack, out statusMSG, cameraAddress);
                CheckGE2048_status("GetTemperature Backside", res, statusMSG);
                tl.LogMessage("Temperatures are", Convert.ToString(temperatureCCD) + " " + Convert.ToString(temperatureBack));
                if ((temperatureBack > temperatureBackMax) || (statusMSG == (int)GE2048_Messages.Message_CoolingTurnedOff))
                {
                    cameraStateCurrent = CameraStates.cameraError;
                    throw new ASCOM.InvalidValueException("Backside CCDTemperature is too high, Cooling control switched off");
                }
                return temperatureCCD;
            }
        }

        public CameraStates CameraState     // Jk ok
        {
            get
            {
                //tl.LogMessage("CameraState Get", cameraStateCurrent.ToString());
                CheckConnected("CameraState");
                return cameraStateCurrent;
            }
        }

        public int CameraXSize      // Jk ok -- size of unbinned full (not cropped) image 
        {
            get
            {
                tl.LogMessage("CameraXSize Get", ccdWidth.ToString());
                return ccdWidth;
            }
        }

        public int CameraYSize      // Jk ok
        {
            get
            {
                tl.LogMessage("CameraYSize Get", ccdHeight.ToString());
                return ccdHeight;
            }
        }

        public bool CanAbortExposure
        {
            get
            {
                tl.LogMessage("CanAbortExposure Get", false.ToString());
                return false;
            }
        }

        public bool CanAsymmetricBin
        {
            get
            {
                tl.LogMessage("CanAsymmetricBin Get", false.ToString());
                return true;
            }
        }

        public bool CanFastReadout
        {
            get
            {
                tl.LogMessage("CanFastReadout Get", false.ToString());
                return false;
            }
        }

        public bool CanGetCoolerPower // TODO JK
        {
            get
            {
                tl.LogMessage("CanGetCoolerPower Get", false.ToString());
                return false;
            }
        }

        public bool CanPulseGuide
        {
            get
            {
                tl.LogMessage("CanPulseGuide Get", false.ToString());
                return false;
            }
        }

        public bool CanSetCCDTemperature // JK ok
        {
            get
            {
                CheckConnected("CanSetCCDTemperature");
                tl.LogMessage("CanSetCCDTemperature Get", true.ToString());
                return true;
            }
        }

        public bool CanStopExposure // JK Ok
        {
            get
            {
                CheckConnected("CanStopExposure");
                tl.LogMessage("CanStopExposure Get", true.ToString());
                return true;
            }
        }
        
        public bool CoolerOn // JK ok
        {
            get
            {
                CheckConnected("CoolerOn get");               
                tl.LogMessage("CoolerOn Get", Convert.ToString(cameraCoolerState));
                return cameraCoolerState;
            }
            set
            {                
                CheckConnected("CoolerOn set");
                tl.LogMessage("CoolerOn Set", Convert.ToString(cameraCoolerState) + " " + Convert.ToString(value));
                if (!value)     // if was switched off
                {
                    bool res = TemperatureControl_SwitchOff(out int statusMSG, cameraAddress);
                    tl.LogMessage("Cooler Off. statusMSG =", Convert.ToString(statusMSG));
                    CheckGE2048_status("Cooler Off", res, statusMSG);                   
                    cameraCoolerState = false;
                }
                else
                {
                    if (ge2048_coolerLevel > numberOfCoolerLevels)
                        throw new ASCOM.InvalidValueException("SetTemperatureLevel", ge2048_coolerLevel.ToString(), " > " + numberOfCoolerLevels.ToString());

                    bool res = TemperatureControl_SetTemperatureLevel(ge2048_coolerLevel, out int statusMSG, cameraAddress);
                    CheckGE2048_status("Cooler On", res, statusMSG);  // fails here
                    //string aboutThisLevel = TemperatureControl_GetLevelString(ge2048_coolerLevel, out statusMSG, cameraAddress);
                    //tl.LogMessage("Cooling level is", aboutThisLevel);
                    cameraCoolerState = true;
                }                
            }
        }

        public double CoolerPower // TODO JK
        {
            get
            {
                tl.LogMessage("CoolerPower Get", "Not implemented");
                throw new ASCOM.PropertyNotImplementedException("CoolerPower", false);
            }
        }

        public double ElectronsPerADU
        {
            get
            {
                // tl.LogMessage("ElectronsPerADU Get", "Not implemented");
                // throw new ASCOM.PropertyNotImplementedException("ElectronsPerADU", false);
                // return Convert.ToDouble(value: Properties.Settings.Default.GainName);
                if (!GE2048_rawGain2preciseDict.ContainsKey(Properties.Settings.Default.GainName))
                {
                    throw new ASCOM.InvalidValueException("ElectronPerADU", Properties.Settings.Default.GainName, "");                    
                }
                return GE2048_rawGain2preciseDict[Properties.Settings.Default.GainName];
            }
        }

        public double ExposureMax // JK Ok
        {
            get
            {
                CheckConnected("ExosureMax");
                tl.LogMessage("ExposureMax Get (ms)", Convert.ToString(maxExposureTime_ms));
                return maxExposureTime_ms * 1000; // msec to sec
            }
        }

        public double ExposureMin       // JK 
        {
            get
            {
                tl.LogMessage("ExposureMin Get", ge2048_exposureMin.ToString());
                //throw new ASCOM.PropertyNotImplementedException("ExposureMin", false);
                return ge2048_exposureMin;    // JK 50 ms
            }
        }

        public double ExposureResolution
        {
            get
            {
                tl.LogMessage("ExposureResolution Get", "Not implemented");
                throw new ASCOM.PropertyNotImplementedException("ExposureResolution", false);
            }
        }

        public bool FastReadout     // JK TODO set fast readout speed from camera settings OR NOT TODO
        {
            get
            {
                tl.LogMessage("FastReadout Get", "Not implemented");
                throw new ASCOM.PropertyNotImplementedException("FastReadout", false);
            }
            set
            {
                tl.LogMessage("FastReadout Set", "value");
                throw new ASCOM.PropertyNotImplementedException("FastReadout", true);
                //if (value) ge2048_readoutSpeed = 3;
                //else ge2048_readoutSpeed = 0;
            }
        }

        public double FullWellCapacity
        {
            get
            {
                tl.LogMessage("FullWellCapacity Get", "Not implemented");
                throw new ASCOM.PropertyNotImplementedException("FullWellCapacity", false);
            }
        }

        public short Gain
        {
            get
            {
                tl.LogMessage("Gain Get", "Not implemented");
                throw new ASCOM.PropertyNotImplementedException("Gain", false);
            }
            set
            {
                tl.LogMessage("Gain Set", "Not implemented");
                throw new ASCOM.PropertyNotImplementedException("Gain", true);
                
            }
        }

        public short GainMax
        {
            get
            {
                tl.LogMessage("GainMax Get", "Not implemented");
                throw new ASCOM.PropertyNotImplementedException("GainMax", false);
            }
        }

        public short GainMin
        {
            get
            {
                tl.LogMessage("GainMin Get", "Not implemented");
                throw new ASCOM.PropertyNotImplementedException("GainMin", true);
            }
        }

        public ArrayList Gains
        {
            get
            {
                tl.LogMessage("Gains Get", "Not implemented");
                throw new ASCOM.PropertyNotImplementedException("Gains", true);               
            }
        }

        public bool HasShutter
        {
            get
            {
                //tl.LogMessage("HasShutter Get", false.ToString());
                return true;    // JK ! check !!!
            }
        }

        public double HeatSinkTemperature       // JK m.b. back_temperature?
        {
            get
            {
                //tl.LogMessage("HeatSinkTemperature Get", "Not implemented");
                // throw new ASCOM.PropertyNotImplementedException("HeatSinkTemperature", false);
                return temperatureBack;
            }
        }

        public object ImageArray        // JK ok
        {
            get
            {
                if (!cameraImageReady)
                {
                    tl.LogMessage("ImageArray Get", "Throwing InvalidOperationException because of a call to ImageArray before the first image has been taken!");
                    throw new ASCOM.InvalidOperationException("Call to ImageArray before the first image has been taken!");
                }                
                tl.LogMessage("ImageArray", "cameraImageArray");                
                return cameraImageArray;
            }
        }

        public object ImageArrayVariant
        {
            get
            {
                if (!cameraImageReady)
                {
                    tl.LogMessage("ImageArrayVariant Get", "Throwing InvalidOperationException because of a call to ImageArrayVariant before the first image has been taken!");
                    throw new ASCOM.InvalidOperationException("Call to ImageArrayVariant before the first image has been taken!");
                }
                cameraImageArrayVariant = new object[cameraNumX, cameraNumY];
                for (int i = 0; i < cameraImageArray.GetLength(1); i++)
                {
                    for (int j = 0; j < cameraImageArray.GetLength(0); j++)
                    {
                        cameraImageArrayVariant[j, i] = cameraImageArray[j, i];
                    }

                }

                return cameraImageArrayVariant;
            }
        }

        public bool ImageReady      // JK ok
        {
            get
            {
                return cameraImageReady;
            }
        }

        public bool IsPulseGuiding
        {
            get
            {
                tl.LogMessage("IsPulseGuiding Get", "Not implemented");
                throw new ASCOM.PropertyNotImplementedException("IsPulseGuiding", false);
            }
        }

        public double LastExposureDuration
        {
            get
            {
                if (!cameraImageReady)
                {
                    tl.LogMessage("LastExposureDuration Get", "Throwing InvalidOperationException because of a call to LastExposureDuration before the first image has been taken!");
                    throw new ASCOM.InvalidOperationException("Call to LastExposureDuration before the first image has been taken!");
                }
                tl.LogMessage("LastExposureDuration Get", cameraLastExposureDuration.ToString());
                return cameraLastExposureDuration;
            }
        }

        public string LastExposureStartTime
        {
            get
            {
                if (!cameraImageReady)
                {
                    tl.LogMessage("LastExposureStartTime Get", "Throwing InvalidOperationException because of a call to LastExposureStartTime before the first image has been taken!");
                    throw new ASCOM.InvalidOperationException("Call to LastExposureStartTime before the first image has been taken!");
                }
                string exposureStartString = exposureStart.ToString("yyyy-MM-ddTHH:mm:ss");
                tl.LogMessage("LastExposureStartTime Get", exposureStartString.ToString());
                return exposureStartString;
            }
        }

        public int MaxADU
        {
            get
            {
                int maxADU = 64000;
                tl.LogMessage("MaxADU Get", Convert.ToString(maxADU));
                return 64000;
            }
        }

        public short MaxBinX // JK Ok
        {
            get
            {
                return ge2048_binningXmax;
            }
        }

        public short MaxBinY // JK Ok
        {
            get
            {
                return ge2048_binningYmax;
            }
        }

        public int NumX  // changes for binned and cropped images
        {
            get
            {
                tl.LogMessage("NumX Get", cameraNumX.ToString());
                return cameraNumX;
            }
            set     // TMP JK Crop image here! Do it !!!
            {
                cameraNumX = value;
                tl.LogMessage("NumX set", value.ToString());
            }
        }

        public int NumY
        {
            get
            {
                tl.LogMessage("NumY Get", cameraNumY.ToString());
                return cameraNumY;
            }
            set
            {
                cameraNumY = value;
                tl.LogMessage("NumY set", value.ToString());
            }
        }

        public int Offset
        {
            get
            {
                tl.LogMessage("Offset Get", "Not implemented");
                throw new ASCOM.PropertyNotImplementedException("Offset", false);
            }
            set
            {
                tl.LogMessage("Offset Set", "Not implemented");
                throw new ASCOM.PropertyNotImplementedException("Offset", true);
            }
        }

        public int OffsetMax
        {
            get
            {
                tl.LogMessage("OffsetMax Get", "Not implemented");
                throw new ASCOM.PropertyNotImplementedException("OffsetMax", false);
            }
        }

        public int OffsetMin
        {
            get
            {
                tl.LogMessage("OffsetMin Get", "Not implemented");
                throw new ASCOM.PropertyNotImplementedException("OffsetMin", true);
            }
        }

        public ArrayList Offsets
        {
            get
            {
                tl.LogMessage("Offsets Get", "Not implemented");
                throw new ASCOM.PropertyNotImplementedException("Offsets", true);
            }
        }

        public short PercentCompleted
        {
            get
            {
                tl.LogMessage("PercentCompleted Get", "Not implemented");
                throw new ASCOM.PropertyNotImplementedException("PercentCompleted", false);
            }
        }

        public double PixelSizeX
        {
            get
            {
                tl.LogMessage("PixelSizeX Get", pixelSize.ToString());
                return pixelSize;
            }
        }

        public double PixelSizeY
        {
            get
            {
                tl.LogMessage("PixelSizeY Get", pixelSize.ToString());
                return pixelSize;
            }
        }

        public void PulseGuide(GuideDirections Direction, int Duration)
        {
            tl.LogMessage("PulseGuide", "Not implemented");
            throw new ASCOM.MethodNotImplementedException("PulseGuide");
        }

        public short ReadoutMode
        {
            get
            {
                tl.LogMessage("ReadoutMode Get", "Not implemented");
                throw new ASCOM.PropertyNotImplementedException("ReadoutMode", false);
                //return (short)ge2048_readoutSpeed;
            }
            set
            {
                tl.LogMessage("ReadoutMode Set", "Not implemented");
                throw new ASCOM.PropertyNotImplementedException("ReadoutMode", true);
                //ge2048_readoutSpeed = 1;
            }
        }

        public ArrayList ReadoutModes
        {
            get
            {
                tl.LogMessage("ReadoutModes Get", "Not implemented");
                throw new ASCOM.PropertyNotImplementedException("ReadoutModes", false);
                //return new ArrayList() { 0, 1, 2, 3, 5 };                
                    
            }
        }

        public string SensorName
        {
            get
            {
                tl.LogMessage("SensorName Get", "Not implemented");
                return "Our fun camera";
                //throw new ASCOM.PropertyNotImplementedException("SensorName", false);
            }
        }

        public SensorType SensorType
        {
            get
            {
                tl.LogMessage("SensorType Get", "Not implemented");
                throw new ASCOM.PropertyNotImplementedException("SensorType", false);
            }
        }

        public double SetCCDTemperature // JK Ok
        {
            get
            {               
                tl.LogMessage("SetCCDTemperature Get", Convert.ToString(cameraSetPointTemperature));
                return cameraSetPointTemperature;
            }
            set
            {
                cameraSetPointTemperature = (int)value; // check it !!!
                bool res = TemperatureControl_SetTemperature(cameraSetPointTemperature, out int statusMSG, cameraAddress);
                tl.LogMessage("SetCCDTemperature Set", Convert.ToString(cameraSetPointTemperature));
                CheckGE2048_status("SetCCDTemperature", res, statusMSG);
            }
        }

        private bool CheckAndReadImage()
        {
            if (DllIsBusy(cameraAddress))
            {
                //tl.LogMessage("DllIsBusy", "True");
                return false;
            }
            else
            {
                // READ IMAGE here
                tl.LogMessage("ImageReady Get", "Yessss!");
                cameraStateCurrent = CameraStates.cameraReading;
                bool res = GetMeasurementData(pInDataStart, out int writeBytes, out int readBytes, out int statusMSG, cameraAddress);
                CheckGE2048_status("GetMeasurementData", res, statusMSG);
                int index = 0;
                for (int i = 0; i < cameraImageArray.GetLength(1); i++)
                {
                    for (int j = 0; j < cameraImageArray.GetLength(0); j++)
                    {
                        cameraImageArray[j, i] = pInDataStart[index];
                        index++;
                    }
                }
                cameraImageReady = true;
                cameraStateCurrent = CameraStates.cameraIdle;
                return true;
            }
        }
        private void AwaitImage()       // for non-blocking exposure
        {
            bool imageIsReady = false;
            while (!imageIsReady)
            {
                imageIsReady = CheckAndReadImage();
                System.Threading.Thread.Sleep(100);
            }
            cameraImageReady = true;
            cameraStateCurrent = CameraStates.cameraIdle;
        }

        private void 
            DoExposure()
        {
            tl.LogMessage("Start of doExposure()", "");
            bool correctBias = false, showSync = false, showShutter = true, triggerMode = false;   // What the hell is all that stuff????
            int triggerTimeOut = 0;

            /* */
            // Non-blocking exposure
            int statusMSG;
            bool res;            
            res = StartMeasurement(correctBias, showSync, showShutter, triggerMode, triggerTimeOut, out statusMSG, cameraAddress);
            CheckGE2048_status("StartMeasurement", res, statusMSG);
            expositionAwaiter = new System.Threading.Thread(AwaitImage);
            expositionAwaiter.IsBackground = true;
            expositionAwaiter.Start();
            return;
            /* */
            /*
            // blocking exposure
            bool res = PerformMeasurement_Blocking(correctBias, showSync, showShutter, triggerMode, triggerTimeOut,
            pInDataStart, out int writeBytes, out int readBytes, out int statusMSG, cameraAddress);
            CheckGE2048_status("GetMeasurementData", res, statusMSG);
            int index = 0;
            for (int i = 0; i < cameraImageArray.GetLength(1); i++)
            {
                for (int j = 0; j < cameraImageArray.GetLength(0); j++)
                {
                    cameraImageArray[j, i] = pInDataStart[index];
                    index++;
                }
            }

            cameraImageReady = true;
            cameraStateCurrent = CameraStates.cameraIdle;
            */
        }
        public void StartExposure(double Duration, bool Light)
        {
            tl.LogMessage("StartExp 1", Duration.ToString() + " " + Light.ToString());
            CheckConnected("Start Exposure");
            if (Light && (Duration < ge2048_exposureMin)) throw new ASCOM.InvalidValueException("StartExposure", Duration.ToString(), " < " + ge2048_exposureMin.ToString());
            if (Duration < 0.0) throw new ASCOM.InvalidValueException("StartExposure", Duration.ToString(), "0.0 upwards");
            
            cameraLastExposureDuration = Duration;
            tl.LogMessage("StartExp 2, numX numY", cameraNumX.ToString() + " " + cameraNumY.ToString());
           
            int exposureTime_ms = Convert.ToInt32(Math.Round(cameraLastExposureDuration * 1000));   // sec to msec    Move it co Connect section?
            
            if (cameraNumX > ccdWidth) throw new ASCOM.InvalidValueException("StartExposure", cameraNumX.ToString(), ccdWidth.ToString());
            if (cameraNumY > ccdHeight) throw new ASCOM.InvalidValueException("StartExposure", cameraNumY.ToString(), ccdHeight.ToString());
            if (cameraStartX > ccdWidth) throw new ASCOM.InvalidValueException("StartExposure", cameraStartX.ToString(), ccdWidth.ToString());
            if (cameraStartY > ccdHeight) throw new ASCOM.InvalidValueException("StartExposure", cameraStartY.ToString(), ccdHeight.ToString());
            
            int statusMSG;
            bool res;
            // Check current camera settings
            res = CamSettings(ge2048_readoutSpeed, exposureTime_ms, cameraXbin, cameraYbin, out int ge2048_numPixelInX, out int ge2048_numPixelInY, out int ge2048_pixelSize, out statusMSG, cameraAddress);
            CheckGE2048_status("CamSettings 1", res, statusMSG);
            if (cameraNumX != ge2048_numPixelInX || cameraNumY != ge2048_numPixelInY)
            {
                int resInt = ActivateCropMode(true, out statusMSG, cameraAddress);
                res = SetupCropMode2D(cameraNumX * cameraXbin, cameraNumY * cameraYbin, out statusMSG, cameraAddress);
                LogMessage("Activate Crop Mode", "resInt = {0} res = {1}", resInt, res);
                tl.LogMessage("SetupCropMode", (cameraNumX * cameraXbin).ToString() + " " + 
                    (cameraNumY * cameraYbin).ToString());
                CheckGE2048_status("SetupCropMode", res, statusMSG);
                
                res = CamSettings(ge2048_readoutSpeed, exposureTime_ms, cameraXbin, cameraYbin,
                    out cameraNumX, out cameraNumY, out ge2048_pixelSize, 
                    out statusMSG, cameraAddress);
                LogMessage("Start Exp settings", "pixel size = {0} cameraNumX = {1} cameraNumY = {2}", pixelSize, cameraNumX, cameraNumY);
                CheckGE2048_status("CamSettings 2", res, statusMSG);
            }
            //int open = Convert.ToInt16(Properties.Settings.Default.ShutterState);    // 0-close, 1-open, 2-auto;
            int open;
            if (Light) open = 2;
            else open = 0;
            res = OpenShutter(open, out statusMSG, cameraAddress);
            CheckGE2048_status("OpenShutter", res, statusMSG);

            //   ------------------- Start Exposure here

            cameraStateCurrent = CameraStates.cameraExposing;
            tl.LogMessage("cameraStateCurrent", cameraStateCurrent.ToString());
            exposureStart = DateTime.Now;
            cameraImageReady = false;

            // Prepare space for a new image
            pInDataStart = new ushort[cameraNumX * cameraNumY];
            cameraImageArray = new int[cameraNumX, cameraNumY];
            LogMessage("Prepare space", "lenX = {0} lenY = {1}", cameraImageArray.GetLength(0), cameraImageArray.GetLength(1));
            if (pInDataStart.GetLength(0) != cameraImageArray.GetLength(0) * cameraImageArray.GetLength(1))
            {
                tl.LogMessage("StartExposure", "ge2048 1-dim array.Length != ASCOM cameraImageArray.Length "
                     + Convert.ToString(pInDataStart.GetLength(0)) + " != " + Convert.ToString(cameraImageArray.GetLength(0) * cameraImageArray.GetLength(1)));
                throw new ASCOM.InvalidValueException("StartExposure:GetMeasurementData", "ge2048 1-dim array.Length != ASCOM cameraImageArray.Length ",
                    Convert.ToString(pInDataStart.GetLength(0)) + " != " + Convert.ToString(cameraImageArray.GetLength(0) * cameraImageArray.GetLength(1)));
            }

            expositionThread = new System.Threading.Thread(new System.Threading.ThreadStart(DoExposure));
            expositionThread.IsBackground = true;
            expositionThread.Start();         
        }

        public int StartX
        {
            get
            {                
                tl.LogMessage("StartX Get", cameraStartX.ToString());
                return cameraStartX;
            }
            set
            {                
                tl.LogMessage("StartX Set", value.ToString());
                if (value != cameraStartX) throw new ASCOM.InvalidValueException("SetStartX", value.ToString() + " != ", cameraStartX.ToString());
                /* cameraStartX = value;
                tl.LogMessage("StartX set", value.ToString()); */
            }
        }

        public int StartY
        {
            get
            {
                tl.LogMessage("StartY Get", cameraStartY.ToString());
                return cameraStartY;
            }
            set
            {
                tl.LogMessage("StartY Set", value.ToString());
                if (value != cameraStartY) throw new ASCOM.InvalidValueException("SetStartY", value.ToString() + " != ", cameraStartY.ToString());
                /* cameraStartY = value;
                tl.LogMessage("StartY set", value.ToString()); */
            }
        }

        public void StopExposure()      // JK ok
        {
            tl.LogMessage("StopExposure", "");
            StopMeasurement(cameraAddress);
        }

        public double SubExposureDuration
        {
            get
            {
                tl.LogMessage("SubExposureDuration Get", "Not implemented");
                throw new ASCOM.PropertyNotImplementedException("SubExposureDuration", false);
            }
            set
            {
                tl.LogMessage("SubExposureDuration Set", "Not implemented");
                throw new ASCOM.PropertyNotImplementedException("SubExposureDuration", true);
            }
        }

        #endregion

        #region Private properties and methods
        // here are some useful properties and methods that can be used as required
        // to help with driver development

        #region ASCOM Registration

        // Register or unregister driver for ASCOM. This is harmless if already
        // registered or unregistered. 
        //
        /// <summary>
        /// Register or unregister the driver with the ASCOM Platform.
        /// This is harmless if the driver is already registered/unregistered.
        /// </summary>
        /// <param name="bRegister">If <c>true</c>, registers the driver, otherwise unregisters it.</param>
        private static void RegUnregASCOM(bool bRegister)
        {
            using (var P = new ASCOM.Utilities.Profile())
            {
                P.DeviceType = "Camera";
                if (bRegister)
                {
                    P.Register(driverID, driverDescription);
                }
                else
                {
                    P.Unregister(driverID);
                }
            }
        }

        /// <summary>
        /// This function registers the driver with the ASCOM Chooser and
        /// is called automatically whenever this class is registered for COM Interop.
        /// </summary>
        /// <param name="t">Type of the class being registered, not used.</param>
        /// <remarks>
        /// This method typically runs in two distinct situations:
        /// <list type="numbered">
        /// <item>
        /// In Visual Studio, when the project is successfully built.
        /// For this to work correctly, the option <c>Register for COM Interop</c>
        /// must be enabled in the project settings.
        /// </item>
        /// <item>During setup, when the installer registers the assembly for COM Interop.</item>
        /// </list>
        /// This technique should mean that it is never necessary to manually register a driver with ASCOM.
        /// </remarks>
        [ComRegisterFunction]
        public static void RegisterASCOM(Type t)
        {
            RegUnregASCOM(true);
        }

        /// <summary>
        /// This function unregisters the driver from the ASCOM Chooser and
        /// is called automatically whenever this class is unregistered from COM Interop.
        /// </summary>
        /// <param name="t">Type of the class being registered, not used.</param>
        /// <remarks>
        /// This method typically runs in two distinct situations:
        /// <list type="numbered">
        /// <item>
        /// In Visual Studio, when the project is cleaned or prior to rebuilding.
        /// For this to work correctly, the option <c>Register for COM Interop</c>
        /// must be enabled in the project settings.
        /// </item>
        /// <item>During uninstall, when the installer unregisters the assembly from COM Interop.</item>
        /// </list>
        /// This technique should mean that it is never necessary to manually unregister a driver from ASCOM.
        /// </remarks>
        [ComUnregisterFunction]
        public static void UnregisterASCOM(Type t)
        {
            RegUnregASCOM(false);
        }

        #endregion

        /// <summary>
        /// Returns true if there is a valid connection to the driver hardware
        /// </summary>
        private bool IsConnected
        {
            get
            {
                // TODO check that the driver hardware connection exists and is connected to the hardware
                return connectedState;
            }
        }

        /// <summary>
        /// Use this function to throw an exception if we aren't connected to the hardware
        /// </summary>
        /// <param name="message"></param>
        private void CheckConnected(string message)
        {
            if (!IsConnected)
            {
                throw new ASCOM.NotConnectedException(message);
            }
        }

        private void CheckGE2048_status(string name, bool res, int statusMSG)
        {
            if (!res)
            {
                string errMessage = GE2048_messageDict[(GE2048_Messages)statusMSG];
                tl.LogMessage(name + "Exception:", errMessage);
                throw new ASCOM.DriverException(errMessage);
            }
        }

        /// <summary>
        /// Read the device configuration from the ASCOM Profile store
        /// </summary>
        /*
            internal void ReadProfile()
            {
            using (Profile driverProfile = new Profile())
                {
                    driverProfile.DeviceType = "Camera";
                    tl.Enabled = Convert.ToBoolean(driverProfile.GetValue(driverID, traceStateProfileName, string.Empty, traceStateDefault));
                    //comPort = driverProfile.GetValue(driverID, comPortProfileName, string.Empty, comPortDefault);
                 //   gain = driverProfile.GetValue(driverID, gainProfileName, string.Empty, gainDefault);

                }
            }
        */
        /// <summary>
        /// Write the device configuration to the  ASCOM  Profile store
        /// </summary>

        /*
        internal void WriteProfile()
        {
            using (Profile driverProfile = new Profile())
            {
                driverProfile.DeviceType = "Camera";
                driverProfile.WriteValue(driverID, traceStateProfileName, tl.Enabled.ToString());
                //comPort = "COM91";
                //driverProfile.WriteValue(driverID, comPortProfileName, comPort.ToString());
                driverProfile.WriteValue(driverID, gainProfileName, gain.ToString());
            }
        }
        */
        /// <summary>
        /// Log helper function that takes formatted strings and arguments
        /// </summary>
        /// <param name="identifier"></param>
        /// <param name="message"></param>
        /// <param name="args"></param>
        internal void LogMessage(string identifier, string message, params object[] args)
        {
            var msg = string.Format(message, args);
            tl.LogMessage(identifier, msg);
        }
        #endregion
    }
}
