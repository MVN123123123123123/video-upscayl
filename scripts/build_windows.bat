@echo off
setlocal enabledelayedexpansion

rem ==============================================================================
rem  Video-Upscayl - Windows Native C++ Backend Build Script (MSVC / CMake / Ninja)
rem ==============================================================================

set "SCRIPT_DIR=%~dp0"
set "ROOT_DIR=%SCRIPT_DIR%.."
set "BUILD_DIR=%ROOT_DIR%\build"

echo ====================================================================
echo  Building Video-Upscayl Native Backend for Windows (x64)
echo ====================================================================

if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%"

rem Check / fetch prebuilt NCNN Windows libraries if missing
if not exist "%ROOT_DIR%\third_party\ncnn\x64\lib\ncnn.lib" (
    echo [INFO] Downloading prebuilt NCNN Windows VS2022 libraries...
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/Tencent/ncnn/releases/download/20260526/ncnn-20260526-windows-vs2022.zip' -OutFile '%ROOT_DIR%\third_party\ncnn_win.zip'; Expand-Archive -Path '%ROOT_DIR%\third_party\ncnn_win.zip' -DestinationPath '%ROOT_DIR%\third_party\ncnn_extracted' -Force; Copy-Item -Recurse -Force '%ROOT_DIR%\third_party\ncnn_extracted\ncnn-20260526-windows-vs2022\*' '%ROOT_DIR%\third_party\ncnn\'; Remove-Item -Force '%ROOT_DIR%\third_party\ncnn_win.zip'; Remove-Item -Recurse -Force '%ROOT_DIR%\third_party\ncnn_extracted'"
)
if exist "%ROOT_DIR%\third_party\ncnn\x64\include" (
    echo [INFO] Syncing Windows x64 NCNN headers to avoid Linux ABI header collisions...
    powershell -Command "Copy-Item -Recurse -Force '%ROOT_DIR%\third_party\ncnn\x64\include\*' '%ROOT_DIR%\third_party\ncnn\include\'"
)

cd /d "%BUILD_DIR%"

rem Clean stale CMakeCache if generated on another machine or folder
if exist "%BUILD_DIR%\CMakeCache.txt" (
    findstr /c:"%BUILD_DIR%" "%BUILD_DIR%\CMakeCache.txt" >nul 2>nul
    if errorlevel 1 (
        echo [INFO] Cleaning stale CMakeCache from another machine or directory...
        del /f /q "%BUILD_DIR%\CMakeCache.txt" 2>nul
        rmdir /s /q "%BUILD_DIR%\CMakeFiles" 2>nul
    )
)

rem Check for Vulkan SDK
if "%VULKAN_SDK%"=="" (
    echo [WARNING] VULKAN_SDK environment variable is not set.
    echo Searching standard Vulkan SDK directory...
    if exist "C:\VulkanSDK\Include" (
        set "VULKAN_SDK=C:\VulkanSDK"
        goto :found_vulkan
    )
    if exist "C:\VulkanSDK" (
        for /f "delims=" %%D in ('dir /b /ad /o-n "C:\VulkanSDK"') do (
            set "VULKAN_SDK=C:\VulkanSDK\%%D"
            goto :found_vulkan
        )
    )
)

:found_vulkan
if not "%VULKAN_SDK%"=="" (
    echo [INFO] Using Vulkan SDK: %VULKAN_SDK%
    set "CMAKE_VULKAN_ARGS=-DVulkan_INCLUDE_DIRS=%VULKAN_SDK%\Include -DVulkan_LIBRARIES=%VULKAN_SDK%\Lib\vulkan-1.lib"
) else (
    echo [WARNING] Vulkan SDK not found. CMake will attempt to find system Vulkan.
    set "CMAKE_VULKAN_ARGS="
)

rem Prefer Ninja if available, else standard CMake Visual Studio generator
where ninja >nul 2>nul
if %ERRORLEVEL% equ 0 (
    cmake -GNinja -DCMAKE_BUILD_TYPE=Release %CMAKE_VULKAN_ARGS% "%ROOT_DIR%\backend"
    ninja
) else (
    cmake -DCMAKE_BUILD_TYPE=Release %CMAKE_VULKAN_ARGS% "%ROOT_DIR%\backend"
    cmake --build . --config Release --parallel
)

if %ERRORLEVEL% equ 0 (
    echo.
    echo ====================================================================
    echo  Build Successful!
    echo ====================================================================
    if exist "%BUILD_DIR%\Release\videoupscaler.dll" (
        copy /y "%BUILD_DIR%\Release\videoupscaler.dll" "%BUILD_DIR%\videoupscaler.dll" >nul
    )
    if exist "%BUILD_DIR%\videoupscaler.dll" (
        echo Built library: %BUILD_DIR%\videoupscaler.dll
    ) else if exist "%BUILD_DIR%\libvideoupscaler.dll" (
        echo Built library: %BUILD_DIR%\libvideoupscaler.dll
    )
) else (
    echo.
    echo [ERROR] Build failed. Please ensure CMake, MSVC C++ compiler, and Vulkan SDK are installed.
    exit /b 1
)
