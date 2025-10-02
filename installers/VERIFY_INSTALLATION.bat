@echo off
echo =========================================================
echo     YS Guardian - Installation Verification
echo =========================================================
echo.

set PLUGIN_DIR=C:\Program Files\Maxon Cinema 4D 2024\plugins\YS_Guardian
set OUTPUT_DIR=C:\YS_Guardian_Output

echo Checking YS Guardian installation...
echo.

echo Plugin Directory:
echo -----------------
if exist "%PLUGIN_DIR%" (
    echo [✓] Plugin directory exists: %PLUGIN_DIR%
    echo.
    echo Files installed:
    dir /B "%PLUGIN_DIR%" 2>nul
    echo.

    echo Critical files check:
    if exist "%PLUGIN_DIR%\ys_guardian_panel.pyp" (
        echo [✓] Main plugin file present
    ) else (
        echo [✗] MISSING: ys_guardian_panel.pyp - Plugin won't load!
    )

    if exist "%PLUGIN_DIR%\exr_converter_external.py" (
        echo [✓] EXR converter with ACES support present
    ) else (
        echo [✗] MISSING: exr_converter_external.py
    )

    if exist "%PLUGIN_DIR%\redshift_snapshot_manager_fixed.py" (
        echo [✓] Snapshot manager present
    ) else (
        echo [✗] MISSING: redshift_snapshot_manager_fixed.py
    )
) else (
    echo [✗] Plugin directory NOT found!
    echo     Expected location: %PLUGIN_DIR%
    echo     Please run INSTALL_YS_GUARDIAN.bat first
)

echo.
echo Output Directory:
echo -----------------
if exist "%OUTPUT_DIR%" (
    echo [✓] Output directory exists: %OUTPUT_DIR%

    if exist "%OUTPUT_DIR%\snapshot_log.txt" (
        echo [✓] Log file exists

        REM Show last few lines of log
        echo.
        echo Recent log entries:
        powershell -Command "Get-Content '%OUTPUT_DIR%\snapshot_log.txt' -Tail 5" 2>nul
    ) else (
        echo [!] Log file not yet created
    )
) else (
    echo [✗] Output directory NOT found
    echo     Will be created on first use
)

echo.
echo Python Environment:
echo -------------------
python --version 2>nul
if %errorlevel% equ 0 (
    echo [✓] Python is installed

    echo.
    echo Checking required packages:
    python -c "import PIL; print('[✓] Pillow:', PIL.__version__)" 2>nul || echo [✗] Pillow not installed
    python -c "import numpy; print('[✓] NumPy:', numpy.__version__)" 2>nul || echo [✗] NumPy not installed
    python -c "import OpenEXR; print('[✓] OpenEXR available')" 2>nul || echo [!] OpenEXR not installed (optional)
) else (
    echo [!] Python not found in PATH
    echo     EXR conversion will be limited
)

echo.
echo =========================================================
echo.
echo If any critical files are missing, please:
echo 1. Run INSTALL_YS_GUARDIAN.bat as Administrator
echo 2. Check that the plugin folder contains all .py files
echo 3. Restart Cinema 4D 2024
echo.
pause