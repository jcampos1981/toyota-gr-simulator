@echo off
REM ============================================================================
REM Monitor de espacio en disco C: durante ejecución del simulador
REM ============================================================================

echo ============================================================================
echo Monitor de Disco C: - Toyota GR Racing Simulator
echo ============================================================================
echo.
echo Presiona Ctrl+C para detener el monitoreo
echo.
echo Timestamp          Free Space (GB)  Change
echo ============================================================================

REM Obtener espacio inicial
for /f "tokens=2 delims==" %%a in ('wmic logicaldisk where "DeviceID='C:'" get FreeSpace /value ^| findstr FreeSpace') do set INITIAL=%%a
set /a INITIAL_GB=%INITIAL:~0,-9%

:LOOP
REM Obtener espacio actual
for /f "tokens=2 delims==" %%a in ('wmic logicaldisk where "DeviceID='C:'" get FreeSpace /value ^| findstr FreeSpace') do set CURRENT=%%a
set /a CURRENT_GB=%CURRENT:~0,-9%

REM Calcular diferencia
set /a DIFF=%CURRENT_GB% - %INITIAL_GB%

REM Mostrar resultado
echo %TIME%       %CURRENT_GB% GB          %DIFF% GB

REM Esperar 5 segundos
timeout /t 5 /nobreak >nul

goto LOOP
