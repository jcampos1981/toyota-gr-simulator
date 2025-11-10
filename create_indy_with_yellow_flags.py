"""
Crear archivo GRANDE de Indianapolis con Yellow Flags y GPS
============================================================
Objetivo: 30-50MB, incluir Yellow Flags
"""

import pandas as pd
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parent.parent
TOYOTA_PROJECT = PROJECT_ROOT.parent
CODE_ROOT = TOYOTA_PROJECT / "Code"

INPUT_FILE = CODE_ROOT / "indianapolis" / "indianapolis" / "R1_indianapolis_motor_speedway_telemetry.csv"
OUTPUT_FILE = PROJECT_ROOT / "simulator" / "sample_data" / "indianapolis_r1_with_yellow_flags.parquet"

print("\n" + "="*70)
print("Creando archivo GRANDE: Indianapolis R1 con Yellow Flags")
print("="*70)
print(f"\nInput: {INPUT_FILE}")
print(f"Output: {OUTPUT_FILE}")

# Verificar tamaño del archivo
file_size_gb = INPUT_FILE.stat().st_size / (1024**3)
print(f"Archivo original: {file_size_gb:.2f} GB")

# Telemetría esencial
ESSENTIAL_TELEMETRY = ['VBOX_Lat_Min', 'VBOX_Long_Minutes', 'speed', 'gear', 'Steering_Angle', 'pbrake_f', 'aps']

print(f"\n[1/4] Cargando datos... (esto tomará varios minutos)")

chunks = []
chunk_size = 2_000_000
max_records_target = 5_000_000  # Objetivo: ~5M registros finales para ~40-50MB

records_accumulated = 0

for i, chunk in enumerate(pd.read_csv(INPUT_FILE, chunksize=chunk_size)):
    print(f"  Chunk {i+1}: {len(chunk):,} registros", end="")

    # Filtrar telemetría esencial
    chunk_filtered = chunk[chunk['telemetry_name'].isin(ESSENTIAL_TELEMETRY)].copy()
    print(f" -> {len(chunk_filtered):,} filtrados", end="")

    # Downsample MUY POCO: 1 de cada 2 (para obtener MUCHOS datos)
    chunk_sampled = chunk_filtered.iloc[::2].copy()
    print(f" -> {len(chunk_sampled):,} downsampled")

    if len(chunk_sampled) > 0:
        chunks.append(chunk_sampled)
        records_accumulated += len(chunk_sampled)

    # Parar cuando tengamos suficientes datos
    if records_accumulated >= max_records_target:
        print(f"  [INFO] Alcanzado objetivo de {max_records_target:,} registros")
        break

print(f"\n[2/4] Combinando {len(chunks)} chunks...")
df = pd.concat(chunks, ignore_index=True)
print(f"  Total registros: {len(df):,}")

print(f"\n[3/4] Procesando datos...")

# Convertir timestamp
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Filtrar primeros 5 vehículos para más variedad y más datos
vehicles = sorted(df['vehicle_id'].unique())[:5]
df = df[df['vehicle_id'].isin(vehicles)].copy()
print(f"  Vehículos seleccionados: {vehicles}")
print(f"  Registros de vehículos: {len(df):,}")

# Convertir GPS a formato correcto
df.loc[df['telemetry_name'] == 'VBOX_Lat_Min', 'telemetry_name'] = 'latitude'
df.loc[df['telemetry_name'] == 'VBOX_Long_Minutes', 'telemetry_name'] = 'longitude'
df.loc[df['telemetry_name'] == 'Steering_Angle', 'telemetry_name'] = 'throttle'
df.loc[df['telemetry_name'] == 'pbrake_f', 'telemetry_name'] = 'brake'

# Convertir GPS de minutos a grados decimales
gps_mask = df['telemetry_name'].isin(['latitude', 'longitude'])
df.loc[gps_mask, 'telemetry_value'] = df.loc[gps_mask, 'telemetry_value'] / 60

# Verificar datos GPS
gps_count = len(df[df['telemetry_name'].isin(['latitude', 'longitude'])])
print(f"  Registros GPS: {gps_count:,} ({gps_count/len(df)*100:.1f}%)")

# Detectar Yellow Flags (velocidad promedio < 50 km/h por ventana de 5s)
print(f"\n  Detectando Yellow Flags...")
speed_data = df[df['telemetry_name'] == 'speed'].copy()
speed_data['time_window'] = speed_data['timestamp'].dt.floor('5S')
avg_speed_by_window = speed_data.groupby('time_window')['telemetry_value'].mean()
yellow_periods = []
in_yellow = False
yellow_start = None

for time_window, speed in avg_speed_by_window.items():
    if speed < 50 and not in_yellow:
        in_yellow = True
        yellow_start = time_window
    elif speed >= 50 and in_yellow:
        yellow_end = time_window
        duration = (yellow_end - yellow_start).total_seconds()
        if duration >= 30:
            yellow_periods.append({
                'start': yellow_start,
                'end': yellow_end,
                'duration': duration
            })
        in_yellow = False

print(f"  Yellow Flags detectados: {len(yellow_periods)}")
for i, yf in enumerate(yellow_periods[:5], 1):
    print(f"    YF{i}: {yf['duration']:.0f}s (desde {yf['start'].strftime('%H:%M:%S')})")

# Seleccionar solo columnas necesarias
df = df[['timestamp', 'vehicle_id', 'telemetry_name', 'telemetry_value']].copy()

print(f"\n[4/4] Guardando archivo...")
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
df.to_parquet(OUTPUT_FILE, index=False, compression='snappy')

file_size_mb = OUTPUT_FILE.stat().st_size / (1024 * 1024)
duration = (df['timestamp'].max() - df['timestamp'].min()).total_seconds()

print(f"\n" + "="*70)
print(f"[OK] COMPLETADO")
print(f"="*70)
print(f"Archivo: {OUTPUT_FILE.name}")
print(f"Tamano: {file_size_mb:.1f} MB")
print(f"Registros: {len(df):,}")
print(f"Vehiculos: {len(vehicles)}")
print(f"Duracion: {duration:.0f}s ({duration/60:.1f} min)")
print(f"Yellow Flags: {len(yellow_periods)}")
print(f"Telemetria: {sorted(df['telemetry_name'].unique())}")
print(f"\nCarga este archivo en el simulador: http://127.0.0.1:8050")
print(f"="*70 + "\n")
