================================================================================
  CREDIEXPRESS POPAYÁN SAS — CONCILIACIÓN BANCARIA
  Guía de Instalación y Ejecución Offline
================================================================================

REQUISITOS DEL SISTEMA
----------------------
  - Windows 10 o 11 (64 bits)
  - Python 3.8 o superior
  - 1 GB de espacio libre en disco (incluye OCR)
  - Navegador web (Chrome, Edge o Firefox)
  - Conexión a internet SOLO para la primera instalación


CÓMO INSTALAR PYTHON (si no lo tiene)
--------------------------------------
  1. Vaya a https://www.python.org/downloads/
  2. Descargue el instalador para Windows (botón amarillo)
  3. Ejecute el instalador
  4. ⚠️ IMPORTANTE: Marque la casilla "Add Python to PATH"
  5. Haga clic en "Install Now"
  6. Espere a que termine y cierre el instalador


CÓMO EJECUTAR LA APLICACIÓN — PRIMERA VEZ
-------------------------------------------
  1. Abra la carpeta "launcher"
  2. Doble clic en "install_and_run.bat"
  3. Si Windows muestra una advertencia, haga clic en "Más información"
     y luego en "Ejecutar de todos modos"
  4. Espere de 5 a 10 minutos mientras se instalan las dependencias
     (solo la primera vez; requiere internet)
  5. El instalador detectará si tiene Tesseract-OCR y poppler.
     Si no los tiene, le guiará para instalarlos.
  6. La aplicación se abrirá automáticamente en su navegador
  7. Ingrese la contraseña para acceder


CÓMO EJECUTAR LA APLICACIÓN — DÍAS SIGUIENTES
-----------------------------------------------
  1. Abra la carpeta "launcher"
  2. Doble clic en "run.bat"
  3. La aplicación se abrirá en segundos (sin instalar nada)


DATOS DE ACCESO
----------------
  Contraseña: crediexpress2025
  (Puede cambiarse en la configuración de Streamlit Cloud)


============================================================
  INSTALACIÓN DE OCR (para PDF escaneados/imágenes)
============================================================

¿Necesito OCR?
  - Si sus PDFs tienen TEXTO DIGITAL (puede seleccionar texto con el mouse):
    NO necesita OCR. El OCR es opcional.
  - Si sus PDFs son IMÁGENES ESCANEADAS (no puede seleccionar texto):
    SÍ necesita OCR.

El instalador (install_and_run.bat) detecta automáticamente si
Tesseract-OCR y poppler están instalados y le guía paso a paso.

INSTALACIÓN MANUAL DE TESSERACT-OCR (si el instalador falla):
  1. Vaya a: https://github.com/UB-Mannheim/tesseract/wiki
  2. Descargue: tesseract-ocr-w64-setup-5.5.0.XXXXXX.exe  (64 bits, ~50 MB)
  3. Ejecute el instalador
  4. En "Choose Components", expanda "Additional language data"
     y marque [x] Spanish
  5. Complete la instalación en: C:\Program Files\Tesseract-OCR\
  6. Vuelva a ejecutar install_and_run.bat

INSTALACIÓN MANUAL DE POPPLER (si el instalador falla):
  1. Vaya a: https://github.com/oschwartz10612/poppler-windows/releases
  2. Descargue: Release-24.08.0-0.zip (~25 MB)
  3. Extraiga el ZIP en: C:\poppler\
     (Debe quedar: C:\poppler\Library\bin\pdftoppm.exe)
  4. Vuelva a ejecutar install_and_run.bat

VERIFICAR QUE OCR FUNCIONA:
  - En la aplicación, vaya al Tab "Diagnóstico"
  - Si un PDF escaneado muestra "🔍 OCR utilizado", está funcionando
  - Si muestra "imagen escaneada y OCR no instalado", revise la instalación


ESTRUCTURA DE CARPETAS
-----------------------
  CONCILIACION BANCARIA/
  ├── launcher/                  ← USTED ESTÁ AQUÍ
  │   ├── install_and_run.bat    ← Primera ejecución + instalación OCR
  │   ├── run.bat                ← Ejecución diaria
  │   └── README.txt             ← Este archivo
  ├── app.py                     ← Aplicación principal
  ├── config.py                  ← Configuración
  ├── storage/                   ← Base de datos (SQLite)
  ├── engine/                    ← Motor de conciliación
  ├── parsers/                   ← Lectura de archivos
  ├── utils/                     ← Utilidades + OCR
  ├── exports/                   ← Exportación Excel
  ├── datos_entrada/             ← Archivos PDF/CSV guardados
  ├── reportes_excel/            ← Reportes Excel generados
  └── requirements.txt           ← Dependencias Python


CÓMO USAR LA APLICACIÓN
-------------------------
  1. En el panel izquierdo, cargue:
     - Extracto Bancario (PDF del banco)
     - Auxiliar Contable (PDF, CSV, Excel o TXT)
  2. Marque "Usar OCR para PDF escaneados" si sus PDFs son imágenes
  3. Haga clic en "Procesar Conciliación"
  4. Explore los 8 tabs con resultados:
     - Diagnóstico    → Calidad de los archivos (incluye info de OCR)
     - Banco          → Movimientos bancarios
     - Auxiliar       → Asientos contables
     - Comparación    → Matches encontrados
     - Diferencias    → Pendientes por conciliar
     - Conciliación   → Cuadre formal
     - Visualizaciones → Gráficos
     - Exportar Excel → Descargar reporte


SOLUCIÓN DE PROBLEMAS
----------------------
  PROBLEMA: "Python no encontrado"
  SOLUCIÓN: Instale Python (vea la sección arriba).
            Si ya lo instaló, reinicie el computador.

  PROBLEMA: No se abre el navegador
  SOLUCIÓN: Abra manualmente: http://localhost:8501

  PROBLEMA: "El puerto 8501 está en uso"
  SOLUCIÓN: Cierre otras aplicaciones que usen ese puerto o
            reinicie el computador.

  PROBLEMA: OCR no funciona / "Error con Tesseract"
  SOLUCIÓN: 1) Instale Tesseract-OCR (sección arriba)
            2) Instale poppler (sección arriba)
            3) Verifique que Tesseract esté en:
               C:\Program Files\Tesseract-OCR\tesseract.exe
            4) Verifique poppler en:
               C:\poppler\Library\bin\pdftoppm.exe
            5) Cierre y vuelva a ejecutar run.bat

  PROBLEMA: Pantalla en blanco o errores
  SOLUCIÓN: Cierre la ventana negra, vuelva a ejecutar run.bat.
            Si persiste, ejecute install_and_run.bat nuevamente.

  PROBLEMA: No se instalaron las dependencias
  SOLUCIÓN: Verifique su conexión a internet e intente de nuevo.


CONTACTO
--------
  CREDIEXPRESS POPAYÁN SAS
  Para soporte técnico, contacte al administrador del sistema.

================================================================================
  v2.0 — Arquitectura Modular | Junio 2025
================================================================================