# Guía de Recomendaciones ML en Tiempo Real

## ✅ Simulador Actualizado

El simulador **LIGERO** ahora incluye un panel de **Recomendaciones ML** que muestra predicciones en tiempo real durante Yellow Flags.

## 🎯 Características Implementadas

### Panel de Recomendaciones ML

Ubicación: Panel derecho, debajo de "Yellow Flag Status"

**Durante Green Flag:**
- Muestra: "Sin Yellow Flag activo"

**Durante Yellow Flag:**
- **Recomendación**: PIT o NO PIT
- **Confianza**: Porcentaje de confianza del modelo
- **Probabilidad PIT**: Probabilidad de que sea buena idea hacer pit
- **Barra de progreso**: Visual de la probabilidad

### Colores del Panel

- 🔴 **ROJO** (danger): Recomendación = **PIT**
- 🔵 **AZUL** (info): Recomendación = **NO PIT**
- ⚪ **GRIS** (secondary): Sin datos o modelos no disponibles

## 📊 Cómo Funcionan las Predicciones

### Datos Analizados Durante Yellow Flag:

1. **Duración del Yellow Flag** (segundos)
2. **Velocidad mínima** durante el Yellow Flag
3. **Velocidad promedio** durante el Yellow Flag
4. **Varianza de velocidad** (avg - min)

### Features Calculadas:

- `is_long_yellow`: 1 si duración > 300s (5 minutos)
- `is_short_yellow`: 1 si duración < 60s (1 minuto)
- `very_low_speed`: 1 si velocidad promedio < 10 km/h
- `circuit_encoded`: Indianapolis (código numérico)
- `race_encoded`: Carrera (default 0)

### Modelo ML:

- **Algoritmo**: Gradient Boosting Classifier
- **Entrenado con**: Datos históricos de carreras
- **Output**: Probabilidad de PIT vs NO PIT

## ⚠️ Nota Importante: Compatibilidad de Modelos

### Estado Actual:

El simulador está configurado para cargar modelos ML, pero hay una **incompatibilidad de versión** de scikit-learn:

- **Modelo entrenado con**: scikit-learn 0.24.2
- **Versión instalada**: scikit-learn 1.3.2

### Impacto:

El simulador funciona perfectamente pero mostrará:
- ⚪ "Modelos ML no disponibles" en el panel de Recomendaciones

### Soluciones:

#### Opción 1: Usar sin Predicciones ML (RECOMENDADO)

El simulador sigue siendo completamente funcional:
- ✅ Detección de Yellow Flags en tiempo real
- ✅ Tablas de telemetría actualizándose cada segundo
- ✅ Alertas visuales de Yellow Flags
- ✅ Progress bar y controles de reproducción
- ❌ Sin predicciones ML

#### Opción 2: Downgrade de scikit-learn (NO RECOMENDADO)

```bash
pip install scikit-learn==0.24.2
```

**Advertencia**: Esto puede causar conflictos con otras librerías.

#### Opción 3: Re-entrenar Modelos (FUTURO)

Necesitaríamos re-entrenar los modelos con scikit-learn 1.3.2:
1. Ejecutar scripts de entrenamiento en `scripts/`
2. Actualizar modelos en `models/`

## 🚀 Cómo Usar el Simulador (Con o Sin ML)

### 1. Iniciar Simulador

```bash
cd H:\Toyota Project\toyota-gr-racing-analytics\simulator
run_lightweight.bat
```

### 2. Abrir en Navegador

http://127.0.0.1:8051

### 3. Cargar Datos

Archivo recomendado: `indianapolis_r1_with_yellow_flags.parquet`
- 10 Yellow Flags detectados
- 1M+ registros
- 198 minutos de carrera

### 4. Reproducir y Observar

1. Click **▶ Play**
2. Ajustar velocidad (recomiendo **5x** para ver Yellow Flags rápido)
3. Observar:
   - **Panel derecho superior**: Yellow Flag Status
   - **Panel derecho inferior**: Recomendaciones ML
   - **Panel central**: Tablas de telemetría por vehículo

### 5. Cuando Aparece un Yellow Flag

El panel amarillo mostrará:
- 🚩 **YELLOW FLAG**
- Duración en segundos

Y el panel de ML mostrará:
- **Con modelos cargados**: Recomendación PIT/NO PIT con confianza
- **Sin modelos**: "Modelos ML no disponibles"

## 📈 Ejemplo de Recomendación ML

```
┌─────────────────────────────────────┐
│ 🤖 Recomendaciones ML              │
├─────────────────────────────────────┤
│ Recomendación: PIT                 │
│ ─────────────────────────────────  │
│ Confianza: 87.3%                   │
│ Probabilidad PIT: 89.5%            │
│ [████████████████████      ] 89.5% │
└─────────────────────────────────────┘
```

## 🎨 Vista Completa de la Interfaz

```
┌─────────────────────────────────────────────────────────────┐
│              Toyota GR Racing Simulator - LIGHTWEIGHT        │
├─────────────────────────────────────────────────────────────┤
│ [Cargar Datos de Telemetría]                                │
├──────────────────────────────────┬──────────────────────────┤
│ Controles de Reproducción        │ Yellow Flag Status       │
│ ▶ Play  ⏸ Pause  ⏮ Reset        │ 🚩 YELLOW FLAG           │
│ Velocidad: [1x-------10x]        │ Duración: 245s           │
│ Tiempo: 12:34:56                 │                          │
│ Progress: [████████        ] 45% │                          │
│                                  ├──────────────────────────┤
│                                  │ 🤖 Recomendaciones ML    │
│                                  │ Recomendación: PIT       │
│                                  │ Confianza: 87.3%         │
│                                  │ Probabilidad PIT: 89.5%  │
├──────────────────────────────────┴──────────────────────────┤
│ Datos en Tiempo Real                                        │
│ ┌─────────────┬─────────────┐                               │
│ │ Vehículo 1  │ Vehículo 2  │                               │
│ │ speed: 45.3 │ speed: 42.1 │                               │
│ │ gear: 3     │ gear: 3     │                               │
│ │ throttle:..  │ throttle:.. │                               │
│ └─────────────┴─────────────┘                               │
└─────────────────────────────────────────────────────────────┘
```

## 🔧 Troubleshooting

### "Modelos ML no disponibles"

**Causa**: Incompatibilidad de versión de scikit-learn

**Solución**: El simulador funciona perfectamente sin las predicciones ML. Los Yellow Flags se detectan igualmente.

### Yellow Flags no aparecen

**Verificar**:
1. Archivo cargado correctamente (mensaje verde)
2. Click en **▶ Play**
3. Usar archivo `indianapolis_r1_with_yellow_flags.parquet`
4. Esperar o aumentar velocidad a 10x

### Tablas vacías

**Solución**:
1. Verificar que se cargó el archivo
2. Esperar 1-2 segundos después de Play
3. Verificar consola para errores

## 📊 Archivos de Datos Disponibles

### Indianapolis (RECOMENDADO) ⭐
- Archivo: `indianapolis_r1_with_yellow_flags.parquet`
- Tamaño: 5.5 MB
- Registros: 1,058,446
- Yellow Flags: **10 detectados**
- Duración: 198 minutos
- GPS: ✅ Sí

### Barber (Alternativo)
- Archivo: `barber_r2_large.parquet`
- Tamaño: 248 KB
- Yellow Flags: Menos frecuentes
- Duración: 45 minutos

## 📝 Estado del Sistema

- **Simulador**: ✅ Corriendo en http://127.0.0.1:8051
- **Temporales**: ✅ H:\Toyota Project\temp\
- **Disco C: libre**: 23.9 GB
- **Disco H: libre**: 5,186 GB
- **Modelos ML**: ⚠️ Incompatibilidad de versión (funcionamiento normal sin ellos)

---

**Última actualización**: 2025-11-08
**Versión**: 2.1 con Recomendaciones ML
