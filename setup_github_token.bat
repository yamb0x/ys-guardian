@echo off
echo ===============================================
echo     GitHub Personal Access Token Setup
echo ===============================================
echo.
echo STEPS TO CREATE A PERSONAL ACCESS TOKEN:
echo.
echo 1. Open your browser and go to:
echo    https://github.com/settings/tokens
echo.
echo 2. Click "Generate new token" button (classic)
echo.
echo 3. Give it a name like "YS Guardian Upload"
echo.
echo 4. Select these scopes:
echo    [x] repo (Full control of private repositories)
echo.
echo 5. Click "Generate token" at the bottom
echo.
echo 6. COPY THE TOKEN (it starts with ghp_)
echo    Important: You won't be able to see it again!
echo.
echo ===============================================
echo.
set /p TOKEN="Paste your token here: "

echo.
echo Setting up GitHub CLI with your token...
echo %TOKEN% | "C:\Program Files\GitHub CLI\gh.exe" auth login --with-token

echo.
echo Testing authentication...
"C:\Program Files\GitHub CLI\gh.exe" auth status

echo.
pause