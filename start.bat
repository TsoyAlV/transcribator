@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto run
where py >nul 2>nul
if errorlevel 1 (
  echo Установите Python 3.12 с https://www.python.org/downloads/ и повторите запуск.
  pause
  exit /b 1
)
py -3.12 -m venv .venv
if errorlevel 1 (
  echo Не удалось создать окружение. Установите Python 3.12.
  pause
  exit /b 1
)
:run
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo Не удалось установить зависимости. Проверьте подключение к интернету.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m streamlit run app.py
pause
