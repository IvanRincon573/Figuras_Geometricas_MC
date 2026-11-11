@echo off
REM Genera dist\FigurasBloques.exe
REM Crea el entorno virtual si no existe, instala dependencias, pasa las pruebas y empaqueta.
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creando entorno virtual...
    py -3 -m venv .venv 2>nul || python -m venv .venv
    if errorlevel 1 (
        echo No se encontro Python. Instala Python 3.10 o superior desde python.org.
        exit /b 1
    )
)

echo Instalando dependencias...
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
".venv\Scripts\python.exe" -m pip install -r requirements-dev.txt || exit /b 1

echo Ejecutando pruebas...
".venv\Scripts\python.exe" -m pytest -q || (
    echo Las pruebas han fallado: no se genera el ejecutable.
    exit /b 1
)

echo Generando ejecutable...
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean FigurasBloques.spec || exit /b 1

echo.
echo Listo: dist\FigurasBloques.exe
endlocal
