#ifndef GREATEYESBETA_H
#define GREATEYESBETA_H


#if defined(_WINDOWS) || defined(_WIN) ||  defined(_WIN32) || defined(_WIN64)
#define _WINDOWS 1
#ifndef DLL_IMPORT_STRING
#define DLL_IMPORT_STRING __declspec(dllimport) 
#endif
#else
#define DLL_IMPORT_STRING
#endif


#include "greateyes.h"


extern "C" DLL_IMPORT_STRING bool StartContinousMeasurement(bool correctBias, bool showSync, bool showShutter, bool triggerMode, int triggerTimeOut, int msDelay, int& statusMSG, int Cam);
// starts continous measurement on camserver
// IN: correctBias          if true, each line will be intensity corrected dependent on the dark pixel values left and right of this line
// IN: showSync        		if true, the sync output of the camera will rise during exposure time otherwise it remains low.
// IN: showShutter			use auto shuter
// IN: triggerMode    		external trigger
// IN: triggerTimeOut		timeout for external trigger
// IN: msDelay				delay in ms between two consecutive measurements
// In: addr					index of connected devices; begins at addr = 0 for first device
// Out: statusMSG           index of status message
// Result: Bool             success true/false

extern "C" DLL_IMPORT_STRING bool StopContinousMeasurement(int& statusMSG, int Cam);
// Stops continous measurement on camserver
// In: addr					index of connected devices; begins at addr = 0 for first device
// Out: statusMSG           index of status message
// Result: Bool             success true/false




#endif