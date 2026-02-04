@echo off
echo Building SteamVR Tracker Jitter Analysis Tool...

REM Clean previous builds
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.spec del *.spec

REM Define path to OpenVR DLL (Using LocalAppData)
set OPENVR_DLL=%LOCALAPPDATA%\Programs\Python\Python310\Lib\site-packages\openvr\libopenvr_api_64.dll

echo Checking for OpenVR DLL at: %OPENVR_DLL%
if not exist "%OPENVR_DLL%" (
    echo WARNING: DLL not found at expected path. Trying absolute path from previous inspection.
    set OPENVR_DLL=C:\Users\shun2\AppData\Local\Programs\Python\Python310\Lib\site-packages\openvr\libopenvr_api_64.dll
)

REM Run PyInstaller with binary inclusion
pyinstaller --noconfirm --onefile --noconsole --name "SteamVR_Jitter_Tool" --hidden-import=PyQt5.sip --add-binary "%OPENVR_DLL%;openvr" main.py

echo.
echo Build complete!
echo Executable is located in the 'dist' folder.
pause
