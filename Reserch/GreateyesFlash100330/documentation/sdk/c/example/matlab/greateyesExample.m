%load greateyes lib
%-------------------------------------
if libisloaded('greateyes')
    unloadlibrary greateyes;
end

pathlib = 'e:\libgreateyes\greateyes.dll';
pathHeader = 'e:\libgreateyes\greateyes.h';

%[notfound,warnings] = loadlibrary('greateyes', @greateyesproto);
[notfound,warnings] = loadlibrary(pathlib, pathHeader);

%display all available functions of greateyes.dll
%libfunctions('greateyes');
%or display all functions of greateyes.dll with datatypes of the parameters
libfunctionsview greateyes;

%get lib version
%-------------------------------------
size = int32(0);
sizePtr = libpointer('int32Ptr', size);
dllVersion = calllib('greateyes','GetDLLVersion',  sizePtr);
size = sizePtr.value;

%get number of connected USB cameras
%-------------------------------------
retValInt = calllib('greateyes', 'GetNumberOfConnectedCams');

if retValInt == 0
    unloadlibrary greateyes;
    return;
end

%connect to USB camera
%-------------------------------------
addr = int32(0);
modelID = -1;
modelIDPtr = libpointer('int32Ptr', modelID);
modelString = '';
modelStringPtr = libpointer('voidPtr',[int8(modelString) 0]);
statusMSG = -1;
statusMSGPtr = libpointer('int32Ptr', statusMSG);
cameraConnected = logical(calllib('greateyes', 'ConnectCamera',modelIDPtr, modelStringPtr, statusMSGPtr, addr));
modelID = modelIDPtr.value;
statusMSG = statusMSGPtr.value;

if cameraConnected == false
    unloadlibrary greateyes;
    return;
end

%init camera
%-------------------------------------
cameraInit = logical(calllib('greateyes', 'InitCamera', statusMSGPtr, addr)); 
statusMSG = statusMSGPtr.value;

if cameraInit == false
    unloadlibrary greateyes;
    return;
end

%setup temperature control
%-------------------------------------
cooingHardwareOption = int32(42223);
minTemperature = int32(25);
maxTemperature = int32(25);
minTemperaturePtr = libpointer('int32Ptr', minTemperature);
maxTemperaturePtr = libpointer('int32Ptr', maxTemperature);
tempConotrolInit = calllib('greateyes', 'TemperatureControl_Init', cooingHardwareOption, minTemperaturePtr, maxTemperaturePtr, statusMSGPtr, addr);   
minTemperature = minTemperaturePtr.value;
maxTemperature = maxTemperaturePtr.value;
statusMSG = statusMSGPtr.value;

if tempConotrolInit <= 0 
    calllib('greateyes', 'DisconnectCamera', statusMSGPtr, addr);
    unloadlibrary greateyes;
    return;
end

%get temperature of sensor 
%-------------------------------------
thermistorSensor = 0;
sensorTemperature = int32(100);
sensorTemperaturePtr = libpointer('int32Ptr', sensorTemperature);
gotSensorTemp =  calllib('greateyes', 'TemperatureControl_GetTemperature', thermistorSensor, sensorTemperaturePtr, statusMSGPtr, addr);   

if gotSensorTemp == true
    sensorTemperature = sensorTemperaturePtr.value;
end

%get TEC backside temperature
%-------------------------------------
thermistorBackside = 1;
backsideTemperature = int32(100);
backsideTemperaturePtr = libpointer('int32Ptr', backsideTemperature);
gotBacksideTemp =  calllib('greateyes', 'TemperatureControl_GetTemperature', thermistorBackside, backsideTemperaturePtr, statusMSGPtr, addr);   

if gotBacksideTemp == true
    backsideTemperature = backsideTemperaturePtr.value;
end

%set bbp = 2
%-------------------------------------
bbpSet = calllib('greateyes', 'SetBitDepth', int32(2), statusMSGPtr, addr);   

%Get image size
%-------------------------------------
width = int32(0);
height = int32(0);
bbp = int32(0);
widthPtr =libpointer('int32Ptr', width);
heightPtr =libpointer('int32Ptr', height);
bbpPtr =libpointer('int32Ptr', bbp);
imgageSizeGot = calllib('greateyes', 'GetImageSize', widthPtr, heightPtr, bbpPtr, addr);   
width = widthPtr.value;
height = heightPtr.value;
bbp = bbpPtr.value;

if imgageSizeGot == false
    calllib('greateyes', 'DisconnectCamera', statusMSGPtr, addr);
    unloadlibrary greateyes;
    return;
end


%Get 16Bit image with default setup 
%-------------------------------------
%start measurement
image = zeros(width, height, 'uint16');
image16Ptr = libpointer('voidPtr', image );
measurementStarted = calllib('greateyes', 'StartMeasurement_DynBitDepth', false, false, false, false, statusMSGPtr, addr);   
statusMSG = statusMSGPtr.value;

if measurementStarted == false
    calllib('greateyes', 'DisconnectCamera', statusMSGPtr, addr);
    unloadlibrary greateyes;
    return;
end
    
%wait for image
cameraBusy = true
while cameraBusy == true
    cameraBusy = calllib('greateyes', 'DllIsBusy', addr);  
end

%get measurement
imageGot = calllib('greateyes', 'GetMeasurementData_DynBitDepth', image16Ptr, statusMSGPtr, addr);   

if imageGot == false
    calllib('greateyes', 'DisconnectCamera', statusMSGPtr, addr);
    unloadlibrary greateyes;
    return;
end

%image contains image data in a 1d array now
image = image16Ptr.VALUE;

%show image
maxVal = int16(max(image(:)));
minVal = int16(min(image(:)));
imshow(image, [minVal maxVal]);

%disconnect camera and exit script
%-------------------------------------
calllib('greateyes', 'DisconnectCamera', statusMSGPtr, addr);
unloadlibrary greateyes;