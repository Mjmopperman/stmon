@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM Get commit message from user
set /p commit_msg="Enter commit message: "

REM Check if message is empty
if "!commit_msg!"=="" (
    echo Error: Commit message cannot be empty
    exit /b 1
)

REM Show what will be committed
echo.
echo === Git Status ===
git status

echo.
echo === Adding all changes ===
git add .

echo.
echo === Committing with message: !commit_msg! ===
git commit -m "!commit_msg!"

if errorlevel 1 (
    echo.
    echo Commit failed. Check for errors above.
    exit /b 1
)

echo.
echo === Pushing to origin master ===
git push origin master

if errorlevel 1 (
    echo.
    echo Push failed. Check for errors above.
    exit /b 1
)

echo.
echo ✅ Done! Changes pushed successfully.

endlocal
