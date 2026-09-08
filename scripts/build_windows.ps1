# Video-Upscayl Windows PowerShell Build Script
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = (Resolve-Path "$ScriptDir\..").Path
$BuildDir = "$RootDir\build"

Write-Host "====================================================================" -ForegroundColor Cyan
Write-Host " Building Video-Upscayl Native Backend for Windows (PowerShell)" -ForegroundColor Cyan
Write-Host "====================================================================" -ForegroundColor Cyan

if (-not (Test-Path $BuildDir)) {
    New-Item -ItemType Directory -Path $BuildDir | Out-Null
}

Set-Location $BuildDir

# Detect Vulkan SDK
$VulkanArgs = @()
if ($env:VULKAN_SDK) {
    Write-Host "[INFO] Vulkan SDK detected at $env:VULKAN_SDK" -ForegroundColor Green
    $VulkanArgs += "-DVulkan_INCLUDE_DIRS=$env:VULKAN_SDK\Include"
    $VulkanArgs += "-DVulkan_LIBRARIES=$env:VULKAN_SDK\Lib\vulkan-1.lib"
} elseif (Test-Path "C:\VulkanSDK") {
    $latest = Get-ChildItem "C:\VulkanSDK" | Sort-Object Name -Descending | Select-Object -First 1
    if ($latest) {
        $sdkPath = $latest.FullName
        Write-Host "[INFO] Found Vulkan SDK at $sdkPath" -ForegroundColor Green
        $VulkanArgs += "-DVulkan_INCLUDE_DIRS=$sdkPath\Include"
        $VulkanArgs += "-DVulkan_LIBRARIES=$sdkPath\Lib\vulkan-1.lib"
    }
}

$hasNinja = (Get-Command ninja -ErrorAction SilentlyContinue) -ne $null
if ($hasNinja) {
    cmake -GNinja -DCMAKE_BUILD_TYPE=Release $VulkanArgs "$RootDir\backend"
    ninja
} else {
    cmake -DCMAKE_BUILD_TYPE=Release $VulkanArgs "$RootDir\backend"
    cmake --build . --config Release --parallel
}

if (Test-Path "$BuildDir\Release\videoupscaler.dll") {
    Copy-Item "$BuildDir\Release\videoupscaler.dll" "$BuildDir\videoupscaler.dll" -Force
}

if (Test-Path "$BuildDir\videoupscaler.dll") {
    Write-Host "`n[SUCCESS] Built: $BuildDir\videoupscaler.dll" -ForegroundColor Green
} elseif (Test-Path "$BuildDir\libvideoupscaler.dll") {
    Write-Host "`n[SUCCESS] Built: $BuildDir\libvideoupscaler.dll" -ForegroundColor Green
} else {
    Write-Host "`n[INFO] Backend compilation complete." -ForegroundColor Green
}
