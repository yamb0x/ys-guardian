@echo off
setlocal EnableDelayedExpansion

REM Keep window open after execution
if "%1" neq "nopause" (
    cmd /k "%~f0" nopause
    exit
)

echo =========================================================
echo     YS Guardian - Python Setup Diagnostic Tool
echo =========================================================
echo.
echo This tool will help diagnose Python installation issues
echo.

REM Check Windows Store aliases
echo Step 1: Checking for Windows Store Python aliases...
echo ----------------------------------------
set STORE_REDIRECT=0

for %%A in ("%LocalAppData%\Microsoft\WindowsApps\python.exe" "%LocalAppData%\Microsoft\WindowsApps\python3.exe" "%LocalAppData%\Microsoft\WindowsApps\py.exe") do (
    if exist "%%~A" (
        echo [WARNING] Found Windows Store alias: %%~A
        set STORE_REDIRECT=1
    )
)

if !STORE_REDIRECT!==1 (
    echo.
    echo Windows Store aliases found!
    echo These can interfere with Python detection.
    echo.
    echo TO FIX:
    echo 1. Open Windows Settings
    echo 2. Search for "App execution aliases"
    echo 3. Turn OFF "python.exe" and "python3.exe"
    echo 4. Click OK and rerun this test
    echo.
)

echo.
echo Step 2: Searching for Python installations...
echo ----------------------------------------

set PYTHON_FOUND=0
set WORKING_PYTHON=

REM Check Program Files
echo Checking Program Files...
for /d %%D in ("C:\Program Files\Python*" "C:\Program Files (x86)\Python*") do (
    if exist "%%D\python.exe" (
        echo [FOUND] Python at: %%D
        "%%D\python.exe" --version 2>nul
        if !errorlevel! equ 0 (
            echo   Status: WORKING
            set PYTHON_FOUND=1
            set WORKING_PYTHON=%%D\python.exe
        ) else (
            echo   Status: NOT WORKING
        )
    )
)

REM Check user local
echo.
echo Checking User Local...
for /d %%D in ("%LocalAppData%\Programs\Python\Python*") do (
    if exist "%%D\python.exe" (
        echo [FOUND] Python at: %%D
        "%%D\python.exe" --version 2>nul
        if !errorlevel! equ 0 (
            echo   Status: WORKING
            set PYTHON_FOUND=1
            set WORKING_PYTHON=%%D\python.exe
        ) else (
            echo   Status: NOT WORKING
        )
    )
)

REM Check PATH commands
echo.
echo Step 3: Checking PATH commands...
echo ----------------------------------------

REM Test py command
where py >nul 2>&1
if %errorlevel% equ 0 (
    echo Testing 'py' command...
    py -c "import sys; print('  Python ' + sys.version)" 2>nul
    if !errorlevel! equ 0 (
        echo   Status: WORKING
        set PYTHON_FOUND=1
        if "!WORKING_PYTHON!"=="" set WORKING_PYTHON=py
    ) else (
        echo   Status: BLOCKED ^(Windows Store redirect^)
    )
) else (
    echo 'py' command: NOT FOUND
)

REM Test python3 command
where python3 >nul 2>&1
if %errorlevel% equ 0 (
    echo Testing 'python3' command...
    python3 -c "import sys; print('  Python ' + sys.version)" 2>nul
    if !errorlevel! equ 0 (
        echo   Status: WORKING
        set PYTHON_FOUND=1
        if "!WORKING_PYTHON!"=="" set WORKING_PYTHON=python3
    ) else (
        echo   Status: BLOCKED ^(Windows Store redirect^)
    )
) else (
    echo 'python3' command: NOT FOUND
)

REM Test python command
where python >nul 2>&1
if %errorlevel% equ 0 (
    echo Testing 'python' command...
    python -c "import sys; print('  Python ' + sys.version)" 2>nul
    if !errorlevel! equ 0 (
        echo   Status: WORKING
        set PYTHON_FOUND=1
        if "!WORKING_PYTHON!"=="" set WORKING_PYTHON=python
    ) else (
        echo   Status: BLOCKED ^(Windows Store redirect^)
    )
) else (
    echo 'python' command: NOT FOUND
)

echo.
echo Step 4: Checking required packages...
echo ----------------------------------------

if !PYTHON_FOUND!==1 (
    echo Using Python: !WORKING_PYTHON!
    echo.

    echo Checking Pillow ^(PIL^)...
    "!WORKING_PYTHON!" -c "import PIL; print('  [OK] Pillow installed')" 2>nul
    if !errorlevel! neq 0 (
        echo   [MISSING] Pillow not installed
        echo   To install: "!WORKING_PYTHON!" -m pip install Pillow
    )

    echo Checking NumPy...
    "!WORKING_PYTHON!" -c "import numpy; print('  [OK] NumPy installed')" 2>nul
    if !errorlevel! neq 0 (
        echo   [MISSING] NumPy not installed
        echo   To install: "!WORKING_PYTHON!" -m pip install numpy
    )
) else (
    echo [ERROR] No working Python found!
)

echo.
echo =========================================================
echo                      DIAGNOSIS SUMMARY
echo =========================================================
echo.

if !PYTHON_FOUND!==1 (
    echo [✓] Python is installed and working!
    echo     Command: !WORKING_PYTHON!
    echo.
    echo Next steps:
    echo 1. Install any missing packages listed above
    echo 2. Rerun the YS Guardian installer
    echo 3. The EXR converter should now work
) else (
    echo [✗] Python is NOT properly installed!
    echo.
    echo To fix this issue:
    echo.
    echo OPTION 1 - Automatic ^(Recommended^):
    echo   1. Run INSTALL_YS_GUARDIAN.bat as Administrator
    echo   2. Choose 'Y' when asked to install Python
    echo   3. The installer will handle everything
    echo.
    echo OPTION 2 - Manual:
    echo   1. Download Python from https://www.python.org/downloads/
    echo   2. During installation, CHECK "Add Python to PATH"
    echo   3. After installation, open Command Prompt and run:
    echo      py -m pip install Pillow numpy
    echo   4. Rerun this test to verify
)

if !STORE_REDIRECT!==1 (
    echo.
    echo [!] IMPORTANT: Disable Windows Store aliases ^(see Step 1 above^)
)

echo.
echo =========================================================
echo.
echo.
echo Test complete. You can close this window now.
echo.