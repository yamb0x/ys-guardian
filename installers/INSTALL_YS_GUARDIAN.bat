@echo off
setlocal EnableDelayedExpansion

echo =========================================================
echo     YS Guardian v1.0 - Professional Installation
echo     Cinema 4D 2024 Quality Control Plugin
echo =========================================================
echo.
echo     Features:
echo     - 5 Real-time quality checks with visual status icons
echo     - Icons display in warning messages when issues detected
echo     - Rounded corners on quality check status bars
echo     - NEW: Render Preset tabs (Previz, Pre-Render, Render, Stills)
echo     - NEW: Force Settings button (standard resolutions at 25fps)
echo     - NEW: Force Vertical button (9:16 aspect for reels/stories)
echo     - NEW: Active Watchers as tab buttons (not checkboxes)
echo     - NEW: Mute All button to hide all quality checks
echo     - Modernized Monitoring Controls with clean tab design
echo     - 4x4 Quick Actions grid with tools:
echo       * Select Bad Lights / Visibility / Cameras
echo       * Vibrate Null creation
echo       * Basic Camera Rig setup
echo       * YS-Alembic Browser
echo       * Plugin Info and Checks
echo     - Redshift snapshot management (Save Still)
echo     - ACES color-accurate EXR to PNG conversion
echo     - Professional UI with consistent tab styling
echo     - Artist workflow organization
echo.
echo =========================================================
echo.
echo IMPORTANT: This installer requires Administrator privileges
echo.
pause

REM Get the project root directory (parent of installers folder)
set PROJECT_ROOT=%~dp0..
set PLUGIN_DIR=%PROJECT_ROOT%\plugin
set ICONS_DIR=%PROJECT_ROOT%\icons
set DEST_DIR=C:\Program Files\Maxon Cinema 4D 2024\plugins\YS_Guardian
set DEST_ICONS_DIR=%DEST_DIR%\icons

REM Check if running as administrator
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Administrator privileges required!
    echo Please right-click and select "Run as Administrator"
    echo.
    pause
    exit /b 1
)

REM Check if Cinema 4D is installed
if not exist "C:\Program Files\Maxon Cinema 4D 2024\" (
    echo.
    echo ERROR: Cinema 4D 2024 not found at default location!
    echo Expected: C:\Program Files\Maxon Cinema 4D 2024\
    echo.
    echo Please edit this script if C4D is installed elsewhere.
    echo.
    pause
    exit /b 1
)

echo.
echo Step 1: Creating plugin directory...
echo ----------------------------------------
if not exist "%DEST_DIR%" (
    mkdir "%DEST_DIR%"
    echo Created: %DEST_DIR%
) else (
    echo Directory exists: %DEST_DIR%
)

echo.
echo Step 2: Installing core plugin files...
echo ----------------------------------------

REM Check if source files exist
if not exist "%PLUGIN_DIR%\ys_guardian_panel.pyp" (
    echo [ERROR] Main plugin file not found at:
    echo        %PLUGIN_DIR%\ys_guardian_panel.pyp
    echo.
    echo Please ensure you're running the installer from the correct location.
    pause
    exit /b 1
)

REM Copy main plugin file
copy /Y "%PLUGIN_DIR%\ys_guardian_panel.pyp" "%DEST_DIR%\ys_guardian_panel.pyp"
if %errorlevel% equ 0 (echo [OK] Main plugin file) else (echo [FAILED] Main plugin file)

REM Copy snapshot manager
copy /Y "%PLUGIN_DIR%\redshift_snapshot_manager_fixed.py" "%DEST_DIR%\redshift_snapshot_manager_fixed.py" >nul
if %errorlevel% equ 0 (echo [OK] Snapshot manager) else (echo [FAILED] Snapshot manager)

REM Copy simple converter (bridges to external converter)
copy /Y "%PLUGIN_DIR%\exr_to_png_converter_simple.py" "%DEST_DIR%\exr_to_png_converter_simple.py" >nul
if %errorlevel% equ 0 (echo [OK] Simple converter bridge) else (echo [FAILED] Simple converter)

REM Copy external converter with ACES color space fix
copy /Y "%PLUGIN_DIR%\exr_converter_external.py" "%DEST_DIR%\exr_converter_external.py" >nul
if %errorlevel% equ 0 (echo [OK] External converter with ACES support) else (echo [FAILED] External converter)

echo.
echo Step 3: Installing UI icons...
echo ----------------------------------------

REM Create icons directory
if not exist "%DEST_ICONS_DIR%" (
    mkdir "%DEST_ICONS_DIR%"
    echo [OK] Created icons directory
)

REM Copy icon files
set ICON_COUNT=0
for %%F in ("%ICONS_DIR%\*.tif" "%ICONS_DIR%\*.png" "%ICONS_DIR%\*.svg") do (
    if exist "%%F" (
        copy /Y "%%F" "%DEST_ICONS_DIR%\" >nul 2>&1
        set /a ICON_COUNT+=1
    )
)

if !ICON_COUNT! gtr 0 (
    echo [OK] Installed !ICON_COUNT! icon files
) else (
    echo [WARNING] No icon files found - UI icons will not display
    echo          Expected location: %ICONS_DIR%
)

echo.
echo Step 3a: Installing C4D asset files...
echo ----------------------------------------

REM Create c4d directory in destination
set DEST_C4D_DIR=%DEST_DIR%\c4d
if not exist "%DEST_C4D_DIR%" (
    mkdir "%DEST_C4D_DIR%"
    echo [OK] Created c4d directory
)

REM Copy C4D asset files
set C4D_DIR=%SCRIPT_DIR%\..\c4d
if exist "%C4D_DIR%\VibrateNull.c4d" (
    copy /Y "%C4D_DIR%\VibrateNull.c4d" "%DEST_C4D_DIR%\VibrateNull.c4d" >nul
    if %errorlevel% equ 0 (
        echo [OK] Copied VibrateNull.c4d asset
    ) else (
        echo [WARNING] Failed to copy VibrateNull.c4d
    )
) else (
    echo [WARNING] VibrateNull.c4d not found in c4d folder
)

echo.
echo Step 4: Creating output directory structure...
echo ----------------------------------------
if not exist "C:\YS_Guardian_Output" (
    mkdir "C:\YS_Guardian_Output"
    echo Created: C:\YS_Guardian_Output

    REM Create log file
    echo YS Guardian Log File > "C:\YS_Guardian_Output\snapshot_log.txt"
    echo Created: %date% %time% >> "C:\YS_Guardian_Output\snapshot_log.txt"
    echo [OK] Log file created
) else (
    echo Directory exists: C:\YS_Guardian_Output
)

echo.
echo Step 5: Setting up external Python converter...
echo ----------------------------------------
echo.
echo The plugin uses your system Python for EXR conversion.
echo Checking for Python installation...

REM Check for Python
set PYTHON_FOUND=0
for %%P in (python python3 py) do (
    %%P --version >nul 2>&1
    if !errorlevel! equ 0 (
        set PYTHON_CMD=%%P
        set PYTHON_FOUND=1
        for /f "tokens=*" %%V in ('%%P --version 2^>^&1') do set PYTHON_VERSION=%%V
        echo [OK] Found: !PYTHON_VERSION!
        goto :python_check_done
    )
)

:python_check_done
if %PYTHON_FOUND% equ 0 (
    echo [WARNING] Python not found in PATH
    echo.
    echo The plugin will still work but EXR to PNG conversion may be limited.
    echo For full functionality, install Python 3.8+ and these packages:
    echo   - pip install Pillow
    echo   - pip install numpy
    echo   - pip install OpenEXR (optional, for better HDR support)
    echo.
) else (
    echo.
    echo Checking required Python packages...

    REM Check for Pillow
    %PYTHON_CMD% -c "import PIL; print('[OK] Pillow version:', PIL.__version__)" 2>nul
    if %errorlevel% neq 0 (
        echo [MISSING] Pillow - Install with: %PYTHON_CMD% -m pip install Pillow
    )

    REM Check for numpy
    %PYTHON_CMD% -c "import numpy; print('[OK] NumPy version:', numpy.__version__)" 2>nul
    if %errorlevel% neq 0 (
        echo [MISSING] NumPy - Install with: %PYTHON_CMD% -m pip install numpy
    )

    REM Check for OpenEXR
    %PYTHON_CMD% -c "import OpenEXR; print('[OK] OpenEXR available')" 2>nul
    if %errorlevel% neq 0 (
        echo [OPTIONAL] OpenEXR - For better HDR support: %PYTHON_CMD% -m pip install OpenEXR-Python
    )
)

echo.
echo Step 5: Creating test script...
echo ----------------------------------------
REM Create a test conversion script
echo # Test YS Guardian EXR Converter > "%DEST_DIR%\test_converter.py"
echo import sys >> "%DEST_DIR%\test_converter.py"
echo import os >> "%DEST_DIR%\test_converter.py"
echo sys.path.insert(0, r'%DEST_DIR%') >> "%DEST_DIR%\test_converter.py"
echo from exr_converter_external import convert_exr_to_png >> "%DEST_DIR%\test_converter.py"
echo. >> "%DEST_DIR%\test_converter.py"
echo if len(sys.argv) ^> 1: >> "%DEST_DIR%\test_converter.py"
echo     exr = sys.argv[1] >> "%DEST_DIR%\test_converter.py"
echo     png = exr.replace('.exr', '_converted.png') >> "%DEST_DIR%\test_converter.py"
echo     print(f'Converting {exr} to {png}...') >> "%DEST_DIR%\test_converter.py"
echo     if convert_exr_to_png(exr, png, 'aces'): >> "%DEST_DIR%\test_converter.py"
echo         print('Success!') >> "%DEST_DIR%\test_converter.py"
echo     else: >> "%DEST_DIR%\test_converter.py"
echo         print('Failed!') >> "%DEST_DIR%\test_converter.py"
echo else: >> "%DEST_DIR%\test_converter.py"
echo     print('Usage: python test_converter.py input.exr') >> "%DEST_DIR%\test_converter.py"

echo [OK] Test script created

echo.
echo =========================================================
echo                 Installation Complete!
echo =========================================================
echo.
echo Plugin installed to:
echo   %DEST_DIR%
echo.
echo Verifying installation...
if exist "%DEST_DIR%\ys_guardian_panel.pyp" (
    echo [✓] Main plugin file installed
) else (
    echo [✗] WARNING: Main plugin file missing!
    echo     Please manually copy ys_guardian_panel.pyp to:
    echo     %DEST_DIR%
)

REM Verify icons installation
set ICONS_OK=0
if exist "%DEST_ICONS_DIR%\lights outside icon.tif" set /a ICONS_OK+=1
if exist "%DEST_ICONS_DIR%\visability trap icon.tif" set /a ICONS_OK+=1
if exist "%DEST_ICONS_DIR%\keyframe sanity icon.tif" set /a ICONS_OK+=1
if exist "%DEST_ICONS_DIR%\camera with non zero shift icon.tif" set /a ICONS_OK+=1
if exist "%DEST_ICONS_DIR%\render preset conlfict icon.tif" set /a ICONS_OK+=1

if !ICONS_OK! geq 5 (
    echo [✓] UI icons installed (!ICONS_OK! status icons found)
) else (
    echo [✗] WARNING: Some icons missing (!ICONS_OK!/5 found)
    echo     Icons may not display properly in the plugin
)
echo.
echo Output directory:
echo   C:\YS_Guardian_Output\
echo.
echo NEXT STEPS:
echo -----------
echo 1. Restart Cinema 4D 2024
echo 2. The plugin will appear in Extensions > YS Guardian Panel
echo.
echo RENDER PRESETS:
echo ---------------
echo Standard settings at 25 fps:
echo   - Previz: 1280x720 @ 25fps
echo   - Pre-Render: 1920x1080 @ 25fps
echo   - Render: 1920x1080 @ 25fps
echo   - Stills: 3840x2160 @ 25fps
echo.
echo Vertical (9:16) for social media:
echo   - Previz: 720x1280 @ 25fps
echo   - Pre-Render: 1080x1920 @ 25fps
echo   - Render: 1080x1920 @ 25fps
echo   - Stills: 2160x3840 @ 25fps
echo.
echo COLOR SPACE NOTES:
echo ------------------
echo The converter now supports ACES color management:
echo   - 'aces' mode: Matches Redshift RenderView (default)
echo   - 'linear' mode: For pre-tone-mapped EXRs
echo   - 'simple' mode: Legacy gamma 2.2
echo   - 'auto' mode: Auto-detects based on values
echo.
echo TEST CONVERTER:
echo ---------------
echo To test EXR conversion:
echo   python "%DEST_DIR%\test_converter.py" your_file.exr
echo.
echo UNINSTALLATION:
echo ---------------
echo To uninstall, simply delete:
echo   %DEST_DIR%
echo.
echo DOCUMENTATION:
echo --------------
echo See docs\YS_Guardian_Documentation.md for full usage guide
echo.
echo =========================================================
echo.
pause