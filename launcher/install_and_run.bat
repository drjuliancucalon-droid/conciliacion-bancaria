@echo off
chcp 65001 >nul
title Instalador Conciliacion Bancaria CREDIEXPRESS

echo ╔══════════════════════════════════════════════════════════════╗
echo ║  CREDIEXPRESS POPAYAN SAS — Conciliacion Bancaria           ║
echo ║  Instalacion y ejecucion offline                            ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

:: 1. Verificar Python
echo [1/7] Verificando Python...
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python no encontrado.
    echo.
    echo Descargue Python 3.10+ desde:
    echo   https://www.python.org/downloads/
    echo.
    echo IMPORTANTE: marque "Add Python to PATH" durante la instalacion.
    pause
    exit /b 1
)
python --version
echo.

:: 2. Crear/activar entorno virtual
echo [2/7] Preparando entorno virtual...
cd /d "%~dp0"
if not exist "venv\" (
    python -m venv venv
    echo Entorno virtual creado.
) else (
    echo Entorno virtual existente.
)

call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo [ERROR] No se pudo activar el entorno virtual.
    pause
    exit /b 1
)
echo.

:: 3. Instalar dependencias Python
echo [3/7] Instalando dependencias Python (puede tomar 2-3 minutos)...
python -m pip install --upgrade pip --quiet
pip install -r ..\requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Fallo instalando dependencias.
    echo Verifique su conexion a internet para la primera instalacion.
    pause
    exit /b 1
)
echo Dependencias Python instaladas correctamente.
echo.

:: 4. Instalar Tesseract-OCR (motor OCR para PDF escaneados)
echo [4/7] Verificando Tesseract-OCR...
set TESSERACT_OK=0
where tesseract >nul 2>nul
if %errorlevel% equ 0 (
    echo Tesseract-OCR ya instalado en el PATH.
    set TESSERACT_OK=1
)
if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
    echo Tesseract-OCR encontrado en C:\Program Files\Tesseract-OCR
    set TESSERACT_OK=1
    set PATH=C:\Program Files\Tesseract-OCR;%PATH%
)
if exist "C:\Program Files (x86)\Tesseract-OCR\tesseract.exe" (
    echo Tesseract-OCR encontrado en C:\Program Files (x86)\Tesseract-OCR
    set TESSERACT_OK=1
    set PATH=C:\Program Files (x86)\Tesseract-OCR;%PATH%
)

if %TESSERACT_OK% equ 0 (
    echo.
    echo ╔══════════════════════════════════════════════════════════════╗
    echo ║  Tesseract-OCR NO ENCONTRADO                                ║
    echo ╚══════════════════════════════════════════════════════════════╝
    echo.
    echo Tesseract-OCR es NECESARIO para leer PDF escaneados (imagenes).
    echo Se abrira el navegador para que lo descargue:
    echo   https://github.com/UB-Mannheim/tesseract/wiki
    echo.
    echo Pasos para instalarlo manualmente:
    echo   1. Descargue tesseract-ocr-w64-setup-5.5.0.XXXXXX.exe
    echo      (version para Windows 64 bits, ~50 MB)
    echo   2. Ejecute el instalador
    echo   3. En la pantalla "Choose Components", marque:
    echo      [x] Additional language data
    echo        [x] Spanish
    echo   4. Instalar en la ruta por defecto:
    echo      C:\Program Files\Tesseract-OCR\
    echo   5. Al terminar, cierre esta ventana y vuelva a ejecutar
    echo      install_and_run.bat
    echo.
    echo NOTA: Si sus PDFs tienen texto digital, no necesita Tesseract.
    echo       Puede continuar sin OCR.
    echo.
    choice /C SN /M "Desea continuar SIN OCR? (S=Si, N=No, abrira navegador)"
    if errorlevel 2 (
        start https://github.com/UB-Mannheim/tesseract/wiki
        echo.
        echo Despues de instalar Tesseract, cierre esta ventana
        echo y vuelva a ejecutar install_and_run.bat
        pause
        exit /b 0
    )
    echo Continuando sin OCR... (PDFs escaneados no funcionaran)
) else (
    echo Tesseract-OCR detectado correctamente ✓
)
echo.

:: 5. Instalar poppler (necesario para pdf2image)
echo [5/7] Verificando poppler (pdf2image)...
set POPPLER_OK=0
where pdftoppm >nul 2>nul
if %errorlevel% equ 0 (
    echo poppler ya instalado en el PATH ✓
    set POPPLER_OK=1
)
if exist "C:\poppler\Library\bin\pdftoppm.exe" (
    echo poppler encontrado en C:\poppler\Library\bin ✓
    set POPPLER_OK=1
    set PATH=C:\poppler\Library\bin;%PATH%
)
if exist "C:\poppler-24.08.0\Library\bin\pdftoppm.exe" (
    echo poppler encontrado en C:\poppler-24.08.0\Library\bin ✓
    set POPPLER_OK=1
    set PATH=C:\poppler-24.08.0\Library\bin;%PATH%
)

if %POPPLER_OK% equ 0 (
    echo.
    echo [INFO] poppler no encontrado. Intentando descarga automatica...
    echo.
    :: Descargar poppler para Windows (Release 24.08.0)
    set POPPLER_URL=https://github.com/oschwartz10612/poppler-windows/releases/download/v24.08.0-0/Release-24.08.0-0.zip
    set POPPLER_ZIP=%TEMP%\poppler.zip
    set POPPLER_DIR=C:\poppler

    echo Descargando poppler (~25 MB)... Espere por favor.
    powershell -Command "& {Invoke-WebRequest -Uri '%POPPLER_URL%' -OutFile '%POPPLER_ZIP%'}" 2>nul
    if %errorlevel% equ 0 (
        echo Extrayendo poppler...
        powershell -Command "& {Expand-Archive -Path '%POPPLER_ZIP%' -DestinationPath '%TEMP%\poppler_extract' -Force}" 2>nul
        if exist "%TEMP%\poppler_extract\poppler-24.08.0\Library\bin" (
            mkdir "%POPPLER_DIR%" 2>nul
            xcopy /E /I /Y "%TEMP%\poppler_extract\poppler-24.08.0\*" "%POPPLER_DIR%\" >nul
            set PATH=%POPPLER_DIR%\Library\bin;%PATH%
            echo poppler instalado en %POPPLER_DIR% ✓
            set POPPLER_OK=1
        )
        del "%POPPLER_ZIP%" 2>nul
        rmdir /S /Q "%TEMP%\poppler_extract" 2>nul
    )

    if %POPPLER_OK% equ 0 (
        echo.
        echo No se pudo instalar poppler automaticamente.
        echo Por favor descarguelo manualmente de:
        echo   https://github.com/oschwartz10612/poppler-windows/releases
        echo Y extraiga en: C:\poppler\
        echo.
        choice /C SN /M "Desea continuar SIN poppler? (S=Si, N=No para salir)"
        if errorlevel 2 exit /b 1
        echo Continuando sin poppler... (PDFs escaneados NO funcionaran)
    )
)
echo.

:: 6. Crear carpetas necesarias
echo [6/7] Preparando carpetas de datos...
if not exist "..\datos_entrada" mkdir "..\datos_entrada"
if not exist "..\reportes_excel" mkdir "..\reportes_excel"
echo.

:: 7. Ejecutar aplicacion
echo [7/7] Iniciando aplicacion...
echo.
echo La aplicacion se abrira en su navegador en unos segundos...
echo Presione Ctrl+C en esta ventana para detenerla.
echo.
timeout /t 2 /nobreak >nul
start http://localhost:8501
streamlit run ..\app.py --server.port 8501 --server.headless false

pause