@echo off
echo ===============================================
echo     Direct Push to GitHub
echo ===============================================
echo.
echo Replace YOUR_USERNAME and YOUR_TOKEN in this file first!
echo.

cd /d "D:\Yambo Studio Dropbox\AI\vibe_coding\ys_guardian"

REM >>> EDIT THESE VALUES <<<
set GITHUB_USER=YOUR_USERNAME
set GITHUB_TOKEN=YOUR_TOKEN

REM Create repository using token
echo Creating repository on GitHub...
curl -H "Authorization: token %GITHUB_TOKEN%" ^
     -d "{\"name\":\"ys-guardian\",\"description\":\"Cinema 4D Quality Control Plugin for Yambo Studio production workflows\",\"private\":false}" ^
     https://api.github.com/user/repos

echo.
echo Adding remote...
git remote add origin https://%GITHUB_TOKEN%@github.com/%GITHUB_USER%/ys-guardian.git

echo.
echo Pushing to GitHub...
git push -u origin main

echo.
echo ===============================================
echo Done! Visit: https://github.com/%GITHUB_USER%/ys-guardian
echo ===============================================
pause