@echo off
setlocal
py CookedTennisAI.py
if errorlevel 1 (
  echo.
  echo Python build failed. If "py" is unavailable, try: python CookedTennisAI.py
  exit /b 1
)
echo.
echo DeepCourt is ready in the Tennis save folder.
pause
