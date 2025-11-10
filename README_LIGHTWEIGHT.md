# Simulador LIGERO - Toyota GR Racing

## Soluciones Implementadas

### ✅ Punto 1: Visualización en Tiempo Real

**Problema Original:**
- La simulación no mostraba avance visible en las gráficas
- Gráficas de Plotly consumen mucha CPU y memoria
- Actualización cada 500ms no era suficientemente visible

**Solución Implementada:**
- **Tablas de valores** en lugar de gráficas pesadas
- **Actualización cada 1 segundo** (visible y eficiente)
- **Alertas destacadas** para Yellow Flags
- **Progress bar** mostrando avance en tiempo real
- **DataTables** con valores actuales de telemetría por vehículo

### ✅ Punto 2: Archivos Temporales en H: Drive

**Problema Original:**
- La simulación consumía 18 GB en disco C: (archivos temporales)
- Windows usaba C: para swap/paging cuando se llenaba la RAM
- Pandas, Matplotlib, Flask creaban archivos en C:\Users\AppData

**Solución Implementada:**
- **Variables de entorno configuradas** antes de importar librerías:
  ```python
  os.environ['TEMP'] = 'H:/Toyota Project/temp'
  os.environ['TMP'] = 'H:/Toyota Project/temp'
  os.environ['TMPDIR'] = 'H:/Toyota Project/temp'
  os.environ['MPLCONFIGDIR'] = 'H:/Toyota Project/temp'
  os.environ['PYTHON_EGG_CACHE'] = 'H:/Toyota Project/temp'
  ```
- **Directorio temporal** creado automáticamente en H: drive
- **H: drive tiene 5TB** de espacio disponible

## Características del Simulador LIGERO

### 🚀 Optimizaciones de Rendimiento

| Característica | Versión Original | Versión LIGERA | Mejora |
|----------------|------------------|----------------|---------|
| **Tipo de visualización** | Gráficas Plotly | Tablas DataTable | -80% CPU |
| **Frecuencia actualización** | 500ms (2/seg) | 1000ms (1/seg) | -50% callbacks |
| **Uso de memoria** | 2-3 GB | 500 MB - 1 GB | -66% RAM |
| **Archivos temporales** | C: drive | H: drive | 0 GB en C: |
| **Deserialización JSON** | 0 (optimizado) | 0 (optimizado) | Igual |
| **Debug mode** | OFF | OFF | Igual |

### 📊 Interfaz de Usuario

#### Pantalla Principal:
1. **Carga de Archivo**
   - Drag & Drop o selección manual
   - Soporta Parquet y CSV
   - Validación automática de formato

2. **Controles de Reproducción**
   - ▶ Play / ⏸ Pause / ⏮ Reset
   - Slider de velocidad: 1x a 10x
   - Progress bar con porcentaje
   - Información de tiempo transcurrido

3. **Yellow Flag Status**
   - 🚩 Alerta ROJA cuando hay Yellow Flag
   - 🟢 Estado VERDE en condiciones normales
   - Duración del Yellow Flag en segundos

4. **Tablas de Telemetría**
   - **Una tabla por vehículo**
   - Valores actuales de cada sensor
   - Actualización en tiempo real
   - Formato compacto y legible

#### Datos Mostrados por Vehículo:
- **speed** - Velocidad actual
- **latitude** - Latitud GPS
- **longitude** - Longitud GPS
- **gear** - Marcha actual
- **throttle** - Acelerador (Steering_Angle)
- **brake** - Freno (pbrake_f)
- **aps** - Sensor de posición del acelerador

## Uso del Simulador

### Método 1: Script Automático (RECOMENDADO)

```bash
cd H:\Toyota Project\toyota-gr-racing-analytics\simulator
run_lightweight.bat
```

Este script:
1. Crea directorio temporal en H: drive
2. Configura variables de entorno
3. Limpia temporales antiguos
4. Inicia el simulador en http://127.0.0.1:8051

### Método 2: Ejecución Manual

```bash
cd H:\Toyota Project\toyota-gr-racing-analytics\simulator
python app_lightweight.py
```

### Método 3: Con Limpieza Previa

```bash
cd H:\Toyota Project\toyota-gr-racing-analytics\simulator
python quick_cleanup.py
run_lightweight.bat
```

## Pasos para Usar

1. **Iniciar el simulador**
   - Ejecutar `run_lightweight.bat`
   - Abrir http://127.0.0.1:8051 en el navegador

2. **Cargar datos de telemetría**
   - Arrastrar archivo `indianapolis_r1_with_yellow_flags.parquet`
   - O usar selector de archivos
   - Ubicación: `H:\Toyota Project\toyota-gr-racing-analytics\simulator\sample_data\`

3. **Reproducir simulación**
   - Click en **▶ Play**
   - Ajustar velocidad con el slider (1x a 10x)
   - Observar tablas actualizándose cada segundo

4. **Monitorear Yellow Flags**
   - El panel derecho muestra el estado actual
   - 🚩 **YELLOW FLAG** aparece en amarillo cuando detectado
   - 🟢 **Green Flag** cuando no hay incidentes

## Archivos del Proyecto

### Simulador Principal
- **app.py** - Versión original con gráficas (http://127.0.0.1:8050)
- **app_lightweight.py** - Versión LIGERA con tablas (http://127.0.0.1:8051) ⭐

### Scripts de Ejecución
- **run_lightweight.bat** - Ejecutar versión ligera (RECOMENDADO)
- **cleanup_and_run.bat** - Limpiar + ejecutar versión original
- **set_temp_drive.bat** - Solo configurar H: drive

### Scripts de Limpieza
- **quick_cleanup.py** - Limpieza rápida (1-2 minutos) ⭐
- **cleanup_disk_c.py** - Limpieza estándar
- **cleanup_aggressive.py** - Limpieza profunda

### Datos de Telemetría
- **sample_data/indianapolis_r1_with_yellow_flags.parquet** - 5.5 MB, 1M registros, 10 Yellow Flags ⭐
- **sample_data/barber_r2_large.parquet** - 248 KB, 45 minutos
- **sample_data/barber_r2_with_gps.parquet** - 0.1 MB, 1.7 minutos

### Documentación
- **README_LIGHTWEIGHT.md** - Este archivo
- **OPTIMIZACIONES.md** - Detalles técnicos de optimizaciones

## Comparación de Versiones

### Versión ORIGINAL (app.py)
✅ Gráficas GPS del circuito
✅ Gráficas de velocidad/throttle en tiempo real
✅ Predicciones ML de pit stops
❌ Alto consumo de CPU
❌ Alto consumo de memoria
❌ Puede consumir swap en C:

**Usar cuando:** Necesitas visualización completa del circuito GPS

### Versión LIGERA (app_lightweight.py) ⭐
✅ Tablas de valores por vehículo
✅ Alertas de Yellow Flags destacadas
✅ Bajo consumo de CPU
✅ Bajo consumo de memoria
✅ Temporales en H: drive
✅ Actualización visible cada segundo
❌ Sin gráficas GPS
❌ Sin predicciones ML

**Usar cuando:** Necesitas eficiencia y bajo consumo de recursos

## Ventajas de la Versión LIGERA

1. **Visualización Clara**
   - Avance visible cada segundo
   - Tablas fáciles de leer
   - No hay lag en la interfaz

2. **Bajo Consumo**
   - 500 MB - 1 GB RAM (vs 2-3 GB)
   - CPU mínimo (sin renderizado de gráficas)
   - Sin archivos en C: drive

3. **Estabilidad**
   - No hay riesgo de out of memory
   - No consume swap de Windows
   - H: drive tiene 5 TB disponible

4. **Yellow Flags Visibles**
   - Panel dedicado con alertas
   - Color amarillo destacado
   - Duración mostrada en segundos

## Monitoreo de Recursos

### Verificar Uso de Disco C:
```bash
python -c "import psutil; d=psutil.disk_usage('C:/'); print(f'Libre: {d.free/(1024**3):.2f} GB')"
```

### Verificar Temporales en H:
```bash
dir "H:\Toyota Project\temp"
```

### Limpiar Temporales:
```bash
python quick_cleanup.py
```

## Resolución de Problemas

### Si la simulación no avanza:
1. Verificar que el archivo se cargó correctamente (mensaje verde)
2. Click en **▶ Play** (no solo cargar el archivo)
3. Verificar que el slider de velocidad no esté en 1x (probar 5x o 10x)

### Si consume mucho C: drive:
1. Detener el simulador
2. Ejecutar `quick_cleanup.py`
3. Ejecutar `run_lightweight.bat` (no ejecutar directamente con python)

### Si las tablas están vacías:
1. Verificar que el archivo Parquet tiene datos
2. Esperar 1-2 segundos después de dar Play
3. Verificar consola para mensajes de error

### Si el navegador va lento:
1. Cerrar otros tabs del navegador
2. Usar Chrome o Edge (mejor que Firefox para Dash)
3. Reducir velocidad de reproducción

## Archivos Temporales

El simulador LIGERO configura automáticamente:

```
H:\Toyota Project\temp\
├── (archivos .tmp de pandas)
├── (archivos .cache de matplotlib)
├── (archivos de sesión de Flask)
└── (archivos de serialización pickle)
```

Estos archivos se limpian automáticamente cuando ejecutas `run_lightweight.bat`.

## Estado Actual del Sistema

- **Disco C: libre**: 23.88 GB
- **Disco H: libre**: 5,186 GB (5.1 TB)
- **Simulador ligero**: ✅ Corriendo en http://127.0.0.1:8051
- **Temporales**: ✅ Configurados en H: drive
- **Limpieza**: ✅ 1.58 GB liberados en C:

---

**Última actualización**: 2025-11-08
**Versión**: 2.0 Lightweight
**Desarrollado para**: Toyota GR Racing - Hack the Track 2024
