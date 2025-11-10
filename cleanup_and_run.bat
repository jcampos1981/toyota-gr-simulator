@echo off
REM ============================================================================
REM Script para limpiar disco C y ejecutar el simulador optimizado
REM ============================================================================

echo ============================================================================
echo Toyota GR Racing Simulator - Optimizado para uso eficiente de disco
echo ============================================================================
echo.

REM Limpiar archivos temporales de Windows
echo [1/5] Limpiando archivos temporales de Windows...
del /q /f /s "%TEMP%\*" 2>nul
del /q /f /s "C:\Windows\Temp\*" 2>nul
echo   [OK] Archivos temporales eliminados

REM Limpiar caché de Python
echo.
echo [2/5] Limpiando cache de Python...
if exist "%LOCALAPPDATA%\pip\cache" (
    rd /s /q "%LOCALAPPDATA%\pip\cache" 2>nul
)
echo   [OK] Cache de Python limpiado

REM Crear directorio temporal en H:
echo.
echo [3/5] Configurando directorio temporal en H: drive...
if not exist "H:\Toyota Project\temp" mkdir "H:\Toyota Project\temp"
echo   [OK] Directorio temporal creado en H:\Toyota Project\temp

REM Configurar variables de entorno
echo.
echo [4/5] Configurando variables de entorno...
set TEMP=H:\Toyota Project\temp
set TMP=H:\Toyota Project\temp
set TMPDIR=H:\Toyota Project\temp
set PYTHON_EGG_CACHE=H:\Toyota Project\temp
set MPLCONFIGDIR=H:\Toyota Project\temp
echo   [OK] Variables configuradas para usar H: drive

REM Mostrar espacio disponible
echo.
echo [5/5] Verificando espacio en disco...
wmic logicaldisk where "DeviceID='C:'" get FreeSpace,Size /format:list | findstr /r "[0-9]"
echo.

echo ============================================================================
echo Iniciando simulador optimizado...
echo ============================================================================
echo.
echo OPTIMIZACIONES APLICADAS:
echo   - Datos cargados en memoria (no JSON)
echo   - Intervalo de actualizacion: 500ms (era 100ms)
echo   - Debug mode: DESHABILITADO
echo   - Archivos temporales: H: drive
echo   - Cache limpiado
echo.
echo Abriendo navegador en: http://127.0.0.1:8050
echo.
echo ============================================================================
echo.

REM Ejecutar simulador
python app.py

pause
