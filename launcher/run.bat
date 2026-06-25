@echo off
chcp 65001 >nul
title Conciliacion Bancaria CREDIEXPRESS

echo ╔══════════════════════════════════════════════════════════════╗
echo ║  CREDIEXPRESS POPAYAN SAS — Conciliacion Bancaria           ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

:: Activar entorno virtual
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo [ERROR] Entorno virtual no encontrado.
    echo Ejecute primero install_and_run.bat para instalar.
    pause
    exit /b 1
)

:: Detectar Tesseract-OCR
where tesseract >nul 2>nul && set PATH=%PATH%
if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
    set PATH=C:\Program Files\Tesseract-OCR;%PATH%
)
if exist "C:\Program Files (x86)\Tesseract-OCR\tesseract.exe" (
    set PATH=C:\Program Files (x86)\Tesseract-OCR;%PATH%
)

:: Detectar poppler
where pdftoppm >nul 2>nul && set PATH=%PATH%
if exist "C:\poppler\Library\bin\pdftoppm.exe" (
    set PATH=C:\poppler\Library\bin;%PATH%
)
if exist "C:\poppler-24.08.0\Library\bin\pdftoppm.exe" (
    set PATH=C:\poppler-24.08.0\Library\bin;%PATH%
)

:: Ejecutar aplicacion
echo Iniciando aplicacion...
echo.
echo La aplicacion se abrira en su navegador en unos segundos...
echo Presione Ctrl+C en esta ventana para detenerla.
echo.
timeout /t 2 /nobreak >nul
start http://localhost:8501
streamlit run ..\app.py --server.port 8501 --server.headless false

pause