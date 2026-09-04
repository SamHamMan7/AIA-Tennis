@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ========================================
echo          DeepCourt Tennis AI
echo ========================================
echo.

set "LIB_DIR=%~dp0..\AIGamePyLibrary"
set "SAVE_DIR=%USERPROFILE%\AppData\LocalLow\Unicorn One\AIComp\Saves\Tennis"

rem ---------------------------------------------------------------------------
rem Ensure AIGamePyLibrary exists next to this repository.
rem ---------------------------------------------------------------------------
if not exist "%LIB_DIR%\AIGamePyLibrary\__init__.py" (
    echo AIGamePyLibrary was not found next to AIA-Tennis.
    echo Trying to clone it automatically...
    echo.

    where git >nul 2>nul
    if errorlevel 1 (
        echo ERROR: Git is not installed or is not on PATH.
        echo Install Git for Windows, then run this file again:
        echo https://git-scm.com/download/win
        goto :fail
    )

    git clone https://github.com/theaia/AIGamePyLibrary.git "%LIB_DIR%"
    if errorlevel 1 (
        echo.
        echo ERROR: Could not clone AIGamePyLibrary.
        goto :fail
    )
) else (
    echo Found AIGamePyLibrary.

    rem Best-effort update. A local edit or network problem should not prevent use
    rem of an otherwise valid installed copy.
    where git >nul 2>nul
    if not errorlevel 1 (
        echo Checking for library updates...
        git -C "%LIB_DIR%" pull --ff-only
        if errorlevel 1 (
            echo WARNING: Library update failed; continuing with the local copy.
        )
    )
)

echo.

rem ---------------------------------------------------------------------------
rem Find Python.
rem ---------------------------------------------------------------------------
set "PYTHON_CMD="
where py >nul 2>nul
if not errorlevel 1 set "PYTHON_CMD=py"

if not defined PYTHON_CMD (
    where python >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
    echo ERROR: Python was not found.
    echo Install Python 3 and enable "Add Python to PATH", then run this again:
    echo https://www.python.org/downloads/
    goto :fail
)

echo Building DeepCourt with %PYTHON_CMD%...
%PYTHON_CMD% "%~dp0CookedTennisAI.py"
if errorlevel 1 (
    echo.
    echo ERROR: DeepCourt build failed.
    goto :fail
)

echo.
echo ========================================
echo DeepCourt built successfully.
echo ========================================
echo.
echo Save file:
echo %SAVE_DIR%\DeepCourt.txt
echo.

if exist "%SAVE_DIR%\DeepCourt.txt" (
    echo Opening the Tennis save folder...
    start "" explorer "%SAVE_DIR%"
) else (
    echo WARNING: The expected DeepCourt.txt file was not found.
)

echo.
echo Launch Aialanders.exe, open Tennis, and select DeepCourt.
echo.
pause
exit /b 0

:fail
echo.
echo Nothing was changed in your game installation.
echo.
pause
exit /b 1
