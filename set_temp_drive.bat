@echo off
REM ============================================================================
REM Configurar variables de entorno para usar H: drive para archivos temporales
REM ============================================================================

echo Configurando variables de entorno para usar H: drive...

REM Crear directorio temporal en H:
if not exist "H:\Toyota Project\temp" mkdir "H:\Toyota Project\temp"

REM Configurar variables de entorno para esta sesión
set TEMP=H:\Toyota Project\temp
set TMP=H:\Toyota Project\temp
set TMPDIR=H:\Toyota Project\temp

REM Variables para Python y Pandas
set PYTHON_EGG_CACHE=H:\Toyota Project\temp
set MPLCONFIGDIR=H:\Toyota Project\temp

echo.
echo [OK] Variables de entorno configuradas:
echo   TEMP=%TEMP%
echo   TMP=%TMP%
echo   TMPDIR=%TMPDIR%
echo.
echo Ejecutando simulador...
echo.

REM Ejecutar simulador con las variables configuradas
python app.py

pause
