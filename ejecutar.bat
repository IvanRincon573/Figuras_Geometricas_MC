@echo off
REM Ejecuta la aplicación desde el código fuente (sin generar el .exe).
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
    echo Creando entorno virtual e instalando PySide6...
    py -3 -m venv .venv 2>nul || python -m venv .venv
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt || exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" main.py %*
endlocal
