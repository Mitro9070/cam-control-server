#include "pch.h"
#include <math.h>
#include "SampleNativeDLL.h"

extern "C" {
	/*int nSampleNativeDLL = 0;
	int fnSampleNativeDLL(void) {
		return 42;
	};

	int SetConnectionType(int type, int& status1, int& status) {
		int mytype = type;

		status = 118 + 177;
		status1 = 111;
		return 156;
	};

	
	int CopyFunc(char* a, char* b) {
		//strcpy(a, b);
		bool ret = false;
		if (a == b) ret = true;
		//return(strlen(b));
		return(ret);
	}
	*/
	
	int shift = 0;

	bool ConnectCamera(int& modelId, char*& modelStr, int& statusMSG, int addr)
	{
		modelId = 1234599;
		const char* const_model_str = "my_SUPER_funky_camera";
		modelStr = const_cast<char*>(const_model_str);   // Uffffff


		statusMSG = 0;
		return true;
	}

	bool DisconnectCamera(int& statusMSG, int addr)
	{
		statusMSG = 0;
		return true;
	}

	int GetMaxExposureTime(int addr)
	{
		return 1000;
	}

	int TemperatureControl_Setup(int coolingHardware, int& statusMSG, int addr)
	{
		statusMSG = 0;
		return 3;
	}

	char* TemperatureControl_GetLevelString(int index, int& statusMSG, int addr)
	{
		statusMSG = 0;
		const char* const_level_str = "-280C";
		char* level_str = const_cast<char*>(const_level_str);
		return level_str;
	}

	bool TemperatureControl_SetTemperatureLevel(int coolingLevel, int& statusMSG, int addr)
	{
		statusMSG = 0;
		return true;
	}

	bool TemperatureControl_SetTemperature(int temperature, int& statusMSG, int addr)
	{
		statusMSG = 0;
		return true;
	}

	bool TemperatureControl_GetTemperature(int thermistor, int& temperature, int& statusMSG, int addr)
	{
		temperature = -90;
		statusMSG = 0;
		return true;
	}

	bool TemperatureControl_SwitchOff(int& statusMSG, int addr)
	{
		statusMSG = 0;
		return true;
	}

	bool CamSettings(int readoutSpeed, int exposureTime_ms, int binningX, int binningY, int& numPixelInX, int& numPixelInY, int& pixelSize, int& statusMSG, int addr)
	{		
		int binX = (int)pow(2, binningX);
		int binY = (int)pow(2, binningY);
		numPixelInX = width / binX;
		numPixelInY = height / binY;
		numX = numPixelInX;
		numY = numPixelInY;
		statusMSG = 0;
		pixelSize = 5.6;
		return true;
	}

	int getMaxBinningX(int& statusMSG, int cameraAddress)
	{
		statusMSG = 0;
		return 4;
	}

	int getMaxBinningY(int& statusMSG, int cameraAddress)
	{
		statusMSG = 0;
		return 4; ;
	}

	bool StartMeasurements(bool CorrectBias, bool showSync, bool showShutter, bool triggerMode, int triggerTimeOut, int& statusMSG, int addr)
	{
		statusMSG = 0;
		return true;
	}

	bool GetMeasuredData(unsigned short* pInDataStart, int& writeBytes, int& readBytes, int& statusMSG, int addr) {
		//unsigned short array[10] = { 1,2,3,4,5,6 };
		for (int i = 0; i < numY * numX; i++) {
				pInDataStart[i] = i + shift;
		}
		writeBytes = 1024;
		readBytes = numX * numY * 2;
		shift += 100;
		return true;
	}

	bool DLLIsBusy(int addr)
	{
		if (dllBusy) {
			dllBusy = false;
		}
		else {
			dllBusy = true;
		}

		return dllBusy;
	}
	
	bool StopMeasurements(int addr) {
		return true;
	}

	bool OpenShutter(int state, int& statusMSG, int addr)
	{
		return true;
	}
	
	bool SetupGain(int gainSeting, int& statusMSG, int addr)
	{
		statusMSG = 0;
		return true;
	}
}
