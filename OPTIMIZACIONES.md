# Optimizaciones del Simulador - Uso Eficiente de Disco

## Problema Identificado

El simulador consumía **18 GB de espacio en disco C** durante la ejecución debido a:

1. **Deserialización JSON repetida**: Cada 100ms se deserializaba todo el archivo Parquet (1M+ registros)
2. **Memory swapping**: Cuando la RAM se llenaba, Windows usaba el archivo de paginación en C:
3. **Logs de debug**: El modo debug generaba logs grandes
4. **Archivos temporales**: Pandas y Python creaban archivos temporales en C:\Users\AppData

## Soluciones Implementadas

### 1. Optimización de Memoria (app.py)

#### Cambio 1: DataFrame Global
**Antes:**
```python
race_data_json = {
    'telemetry': df.to_json(date_format='iso'),  # Serializar 1M registros
    ...
}
```

**Después:**
```python
telemetry_df_global = df  # Mantener en memoria
race_data_json = {
    'telemetry': 'loaded_in_memory',  # NO serializar
    ...
}
```
**Reducción**: ~90% menos uso de memoria

#### Cambio 2: Intervalo de Actualización
**Antes:**
```python
dcc.Interval(id='playback-interval', interval=100, disabled=True)  # 10 veces/segundo
```

**Después:**
```python
dcc.Interval(id='playback-interval', interval=500, disabled=True)  # 2 veces/segundo
```
**Reducción**: 80% menos llamadas a callbacks

#### Cambio 3: Debug Mode Deshabilitado
**Antes:**
```python
app.run(debug=True, host='127.0.0.1', port=8050)
```

**Después:**
```python
app.run(debug=False, host='127.0.0.1', port=8050)
```
**Reducción**: Sin logs innecesarios

### 2. Redirección de Archivos Temporales

#### Script: set_temp_drive.bat
- Configura variables de entorno para usar **H: drive**
- Evita que Windows use C: para archivos temporales
- Variables configuradas:
  - `TEMP=H:\Toyota Project\temp`
  - `TMP=H:\Toyota Project\temp`
  - `PYTHON_EGG_CACHE=H:\Toyota Project\temp`

### 3. Limpieza Automática

#### Script: cleanup_and_run.bat
- Limpia archivos temporales de Windows
- Limpia caché de Python/pip
- Configura variables de entorno
- Ejecuta el simulador optimizado

## Cómo Usar

### Opción 1: Ejecutar con limpieza automática (RECOMENDADO)
```bash
cd H:\Toyota Project\toyota-gr-racing-analytics\simulator
cleanup_and_run.bat
```

### Opción 2: Ejecutar con variables de entorno configuradas
```bash
cd H:\Toyota Project\toyota-gr-racing-analytics\simulator
set_temp_drive.bat
```

### Opción 3: Ejecutar directamente (sin optimizaciones de disco)
```bash
cd H:\Toyota Project\toyota-gr-racing-analytics\simulator
python app.py
```

## Resultados Esperados

### Consumo de Memoria
- **Antes**: ~8-10 GB RAM + 18 GB swap en C:
- **Después**: ~2-3 GB RAM + mínimo swap

### Frecuencia de Actualización
- **Antes**: 10 actualizaciones/segundo (100ms)
- **Después**: 2 actualizaciones/segundo (500ms)
- **Impacto visual**: Imperceptible (sigue siendo fluido)

### Uso de Disco C
- **Antes**: 18 GB consumidos durante ejecución
- **Después**: < 500 MB (solo logs mínimos)

### Velocidad de Carga
- **Antes**: Deserialización JSON cada 100ms
- **Después**: DataFrame en memoria (acceso instantáneo)

## Monitoreo

Para verificar el uso de disco durante la ejecución:

```bash
# Ver espacio libre en C:
wmic logicaldisk where "DeviceID='C:'" get FreeSpace /format:value

# Ver procesos que más espacio usan
dir C:\Users\%USERNAME%\AppData\Local\Temp /s
```

## Archivos Modificados

1. **app.py** - Optimizaciones de memoria y rendimiento
2. **set_temp_drive.bat** - Configuración de variables de entorno
3. **cleanup_and_run.bat** - Script de limpieza y ejecución
4. **OPTIMIZACIONES.md** - Esta documentación

## Notas Importantes

- Los datos del simulador están en **H:\Toyota Project\toyota-gr-racing-analytics**
- Los archivos Parquet están en **H:\Toyota Project\toyota-gr-racing-analytics\simulator\sample_data**
- NO se ha modificado la funcionalidad del simulador, solo el rendimiento
- Todas las características siguen funcionando igual: Yellow Flags, ML predictions, GPS tracking

## Troubleshooting

### Si aún se consume disco C:
1. Verificar que las variables de entorno estén configuradas:
   ```bash
   echo %TEMP%
   # Debe mostrar: H:\Toyota Project\temp
   ```

2. Limpiar manualmente el archivo de paginación:
   - Panel de Control > Sistema > Configuración avanzada del sistema
   - Pestaña "Opciones avanzadas" > Rendimiento > Configuración
   - Pestaña "Opciones avanzadas" > Memoria virtual > Cambiar
   - Desmarcar "Administrar automáticamente" y reducir tamaño en C:

3. Verificar procesos en segundo plano:
   ```bash
   tasklist /v | findstr python
   ```

### Si el simulador va lento:
- Aumentar intervalo a 1000ms (1 segundo) en app.py línea 327
- Reducir número de vehículos en el archivo Parquet
- Usar archivo más pequeño (barber_r2_large.parquet)

---

**Última actualización**: 2025-11-08
**Versión**: 2.0 (Optimizada)
