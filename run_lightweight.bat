@echo off
REM ============================================================================
REM Ejecutar Simulador LIGERO con temporales en H: drive
REM ============================================================================

echo ============================================================================
echo Toyota GR Racing Simulator - VERSION LIGERA
echo ============================================================================
echo.

REM Crear directorio temporal en H:
if not exist "H:\Toyota Project\temp" mkdir "H:\Toyota Project\temp"

REM Configurar variables de entorno PERMANENTEMENTE para esta sesion
set TEMP=H:\Toyota Project\temp
set TMP=H:\Toyota Project\temp
set TMPDIR=H:\Toyota Project\temp
set PYTHON_EGG_CACHE=H:\Toyota Project\temp
set MPLCONFIGDIR=H:\Toyota Project\temp
set NUMEXPR_MAX_THREADS=2
set OMP_NUM_THREADS=2

echo [CONFIG] Variables de entorno configuradas:
echo   TEMP=%TEMP%
echo   TMP=%TMP%
echo.

REM Limpiar archivos temporales antiguos
echo [CLEANUP] Limpiando archivos temporales antiguos...
del /q "H:\Toyota Project\temp\*.*" 2>nul
echo   [OK] Temporales limpiados
echo.

echo [INFO] Caracteristicas de esta version:
echo   - Tablas de valores (no graficas pesadas)
echo   - Actualizacion cada 1 segundo
echo   - Uso minimo de CPU y memoria
echo   - Alertas de Yellow Flags en tiempo real
echo   - Archivos temporales en H: drive
echo.

echo ============================================================================
echo Iniciando simulador ligero en: http://127.0.0.1:8051
echo ============================================================================
echo.

REM Ejecutar simulador ligero
python app_lightweight.py

pause
