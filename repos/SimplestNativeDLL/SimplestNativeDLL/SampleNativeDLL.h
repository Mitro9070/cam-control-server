#pragma once
	// JK JK JK JK
#ifdef SAMPLENATIVEDLL_EXPORTS
#define SAMPLENATIVEDLL_API __declspec(dllexport)
#else
#define SAMPLENATIVEDLL_API __declspec(dllimport)
#endif

//extern "C" SAMPLENATIVEDLL_API int nSampleNativeDLL;
//extern "C" SAMPLENATIVEDLL_API int fnSampleNativeDLL(void);
//extern "C" SAMPLENATIVEDLL_API int CopyFunc(char* a, char* b);
//extern "C" SAMPLENATIVEDLL_API bool GetMeasuredData(unsigned short* pInDataStart, int& writebytes);
//extern "C" SAMPLENATIVEDLL_API int SetConnectionType(int type, int& status1, int& status);
extern "C" SAMPLENATIVEDLL_API bool  ConnectCamera(int& modelId, char*& modelStr, int& statusMSG, int addr);
extern "C" SAMPLENATIVEDLL_API bool  DisconnectCamera(int& statusMSG, int addr);
extern "C" SAMPLENATIVEDLL_API int   GetMaxExposureTime(int addr);
extern "C" SAMPLENATIVEDLL_API int   TemperatureControl_Setup(int coolingHardware, int& statusMSG, int addr);
extern "C" SAMPLENATIVEDLL_API char* TemperatureControl_GetLevelString(int index, int& statusMSG, int addr);
extern "C" SAMPLENATIVEDLL_API bool  TemperatureControl_SetTemperatureLevel(int coolingLevel, int& statusMSG, int addr);
extern "C" SAMPLENATIVEDLL_API bool  TemperatureControl_SetTemperature(int temperature, int& statusMSG, int addr);
extern "C" SAMPLENATIVEDLL_API bool  TemperatureControl_GetTemperature(int thermistor, int& temperature, int& statusMSG, int addr);
extern "C" SAMPLENATIVEDLL_API bool  TemperatureControl_SwitchOff(int& statusMSG, int addr);

extern "C" SAMPLENATIVEDLL_API bool  CamSettings(int readoutSpeed, int exposureTime_ms, int binningX, int binningY, int& numPixelInX, int& numPixelInY, int& pixelSize, int& statusMSG, int addr);
extern "C" SAMPLENATIVEDLL_API int   getMaxBinningX(int& statusMSG, int cameraAddress);
extern "C" SAMPLENATIVEDLL_API int   getMaxBinningY(int& statusMSG, int cameraAddress);
extern "C" SAMPLENATIVEDLL_API bool  StartMeasurements(bool CorrectBias, bool showSync, bool showShutter, bool triggerMode, int triggerTimeOut, int& statusMSG, int addr);
extern "C" SAMPLENATIVEDLL_API bool  GetMeasuredData(unsigned short* pInDataStart, int& writeBytes, int& readBytes, int& statusMSG, int addr);
extern "C" SAMPLENATIVEDLL_API bool  StopMeasurements(int addr);
extern "C" SAMPLENATIVEDLL_API bool  OpenShutter(int state, int& statusMSG, int addr);

extern "C" SAMPLENATIVEDLL_API bool SetupGain(int gainSeting, int& statusMSG, int addr);
extern "C" SAMPLENATIVEDLL_API bool DLLIsBusy(int addr);

static const int width  = 100;
static const int height = 50;
int numX = width;
int numY = height;
static bool dllBusy = true;







