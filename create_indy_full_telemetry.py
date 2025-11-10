"""
Crear archivo GRANDE de Indianapolis con TODA la telemetría
===========================================================
Objetivo: 10-20MB, todas las columnas, más registros
"""

import pandas as pd
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parent.parent
TOYOTA_PROJECT = PROJECT_ROOT.parent
CODE_ROOT = TOYOTA_PROJECT / "Code"

INPUT_FILE = CODE_ROOT / "indianapolis" / "indianapolis" / "R1_indianapolis_motor_speedway_telemetry.csv"
OUTPUT_FILE = PROJECT_ROOT / "simulator" / "sample_data" / "indianapolis_r1_full_telemetry.parquet"

print("\n" + "="*70)
print("Creando archivo con TODA la telemetría: Indianapolis R1")
print("="*70)
print(f"\nInput: {INPUT_FILE}")
print(f"Output: {OUTPUT_FILE}")

# Verificar tamaño del archivo
file_size_gb = INPUT_FILE.stat().st_size / (1024**3)
print(f"Archivo original: {file_size_gb:.2f} GB")

# TODAS las columnas de telemetría disponibles
ALL_TELEMETRY = [
    'VBOX_Lat_Min',       # GPS Latitud
    'VBOX_Long_Minutes',  # GPS Longitud
    'speed',              # Velocidad
    'gear',               # Marcha
    'Steering_Angle',     # Ángulo de dirección (throttle)
    'pbrake_f',           # Freno delantero
    'pbrake_r',           # Freno trasero
    'aps',                # Sensor posición acelerador
    'nmot',               # RPM del motor
    'accx_can',           # Aceleración lateral X
    'accy_can',           # Aceleración longitudinal Y
    'Laptrigger_lapdist_dls'  # Distancia en vuelta
]

print(f"\n[INFO] Columnas a incluir: {len(ALL_TELEMETRY)}")
for col in ALL_TELEMETRY:
    print(f"  - {col}")

print(f"\n[1/5] Cargando datos... (esto tomará varios minutos)")

chunks = []
chunk_size = 2_000_000
max_records_target = 3_000_000  # Menos registros pero MÁS columnas = archivo similar

records_accumulated = 0

for i, chunk in enumerate(pd.read_csv(INPUT_FILE, chunksize=chunk_size)):
    print(f"  Chunk {i+1}: {len(chunk):,} registros", end="")

    # Filtrar TODA la telemetría
    chunk_filtered = chunk[chunk['telemetry_name'].isin(ALL_TELEMETRY)].copy()
    print(f" -> {len(chunk_filtered):,} filtrados", end="")

    # SIN downsampling: queremos TODOS los datos
    # (antes era 1 de cada 2, ahora todos)
    chunk_sampled = chunk_filtered.copy()
    print(f" -> {len(chunk_sampled):,} incluidos")

    if len(chunk_sampled) > 0:
        chunks.append(chunk_sampled)
        records_accumulated += len(chunk_sampled)

    # Parar cuando tengamos suficientes datos
    if records_accumulated >= max_records_target:
        print(f"  [INFO] Alcanzado objetivo de {max_records_target:,} registros")
        break

print(f"\n[2/5] Combinando {len(chunks)} chunks...")
df = pd.concat(chunks, ignore_index=True)
print(f"  Total registros: {len(df):,}")

print(f"\n[3/5] Procesando datos...")

# Convertir timestamp
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Solo 2 vehículos para tener MÁS datos por vehículo
vehicles = sorted(df['vehicle_id'].unique())[:2]
df = df[df['vehicle_id'].isin(vehicles)].copy()
print(f"  Vehículos seleccionados: {vehicles}")
print(f"  Registros de vehículos: {len(df):,}")

# Renombrar columnas a nombres más legibles
rename_map = {
    'VBOX_Lat_Min': 'latitude',
    'VBOX_Long_Minutes': 'longitude',
    'Steering_Angle': 'steering',
    'pbrake_f': 'brake_front',
    'pbrake_r': 'brake_rear',
    'aps': 'throttle_pos',
    'nmot': 'rpm',
    'accx_can': 'acc_x',
    'accy_can': 'acc_y',
    'Laptrigger_lapdist_dls': 'lap_distance'
}

for old_name, new_name in rename_map.items():
    df.loc[df['telemetry_name'] == old_name, 'telemetry_name'] = new_name

# Convertir GPS de minutos a grados decimales
for telem in ['latitude', 'longitude']:
    mask = df['telemetry_name'] == telem
    if mask.any():
        df.loc[mask, 'telemetry_value'] = df.loc[mask, 'telemetry_value'] / 60

print(f"\n[4/5] Detectando Yellow Flags...")

# Detectar Yellow Flags: velocidad < 50 km/h sostenida
speed_data = df[df['telemetry_name'] == 'speed'].copy()
speed_data = speed_data.sort_values('timestamp')

# Crear ventanas de 5 segundos
speed_data['window'] = speed_data.groupby('vehicle_id')['timestamp'].transform(
    lambda x: (x - x.min()).dt.total_seconds() // 5
)

# Velocidad promedio por ventana
window_speed = speed_data.groupby(['vehicle_id', 'window']).agg({
    'telemetry_value': 'mean',
    'timestamp': 'first'
}).reset_index()

# Yellow Flag: velocidad < 50 km/h
window_speed['is_yellow'] = window_speed['telemetry_value'] < 50

# Encontrar períodos continuos de Yellow Flag
yellow_flags = []
for vehicle_id in window_speed['vehicle_id'].unique():
    veh_data = window_speed[window_speed['vehicle_id'] == vehicle_id].sort_values('window')

    in_yellow = False
    yellow_start = None

    for idx, row in veh_data.iterrows():
        if row['is_yellow'] and not in_yellow:
            yellow_start = row['timestamp']
            in_yellow = True
        elif not row['is_yellow'] and in_yellow:
            yellow_end = row['timestamp']
            duration = (yellow_end - yellow_start).total_seconds()

            # Solo Yellow Flags de al menos 30 segundos
            if duration >= 30:
                yellow_flags.append({
                    'start': yellow_start.isoformat(),
                    'end': yellow_end.isoformat(),
                    'duration': duration
                })
            in_yellow = False

print(f"  [OK] {len(yellow_flags)} Yellow Flags detectados")
for i, yf in enumerate(yellow_flags, 1):
    print(f"    {i}. Inicio: {yf['start'][:19]} | Duración: {yf['duration']:.0f}s")

print(f"\n[5/5] Guardando archivo...")
output_size_mb = len(df) * 50 / 1_000_000  # Estimación
print(f"  Tamaño estimado: {output_size_mb:.1f} MB")

df.to_parquet(
    OUTPUT_FILE,
    engine='pyarrow',
    compression='snappy',
    index=False
)

actual_size_mb = OUTPUT_FILE.stat().st_size / (1024**2)
print(f"  [OK] Archivo guardado: {actual_size_mb:.2f} MB")

# Resumen
print("\n" + "="*70)
print("RESUMEN")
print("="*70)
print(f"Registros totales:    {len(df):,}")
print(f"Vehículos:            {len(df['vehicle_id'].unique())}")
print(f"Columnas telemetría:  {len(df['telemetry_name'].unique())}")
print(f"Duración:             {(df['timestamp'].max() - df['timestamp'].min()).total_seconds() / 60:.1f} minutos")
print(f"Yellow Flags:         {len(yellow_flags)}")
print(f"Tamaño archivo:       {actual_size_mb:.2f} MB")
print(f"Ubicación:            {OUTPUT_FILE}")
print("="*70)
