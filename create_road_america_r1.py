"""
Crear archivo de Road America R1 con TODA la telemetría
========================================================
Road America - Circuito de carretera rápido
"""

import pandas as pd
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parent.parent
TOYOTA_PROJECT = PROJECT_ROOT.parent
CODE_ROOT = TOYOTA_PROJECT / "Code"

INPUT_FILE = CODE_ROOT / "road-america" / "road-america" / "Road America" / "Race 1" / "R1_road_america_telemetry_data.csv"
OUTPUT_FILE = PROJECT_ROOT / "simulator" / "sample_data" / "road_america_r1_telemetry.parquet"

print("\n" + "="*70)
print("Creando archivo: Road America R1 con telemetría completa")
print("="*70)
print(f"\nInput: {INPUT_FILE}")
print(f"Output: {OUTPUT_FILE}")

# Verificar tamaño del archivo
file_size_gb = INPUT_FILE.stat().st_size / (1024**3)
print(f"Archivo original: {file_size_gb:.2f} GB")

# TODAS las columnas de telemetría disponibles
ALL_TELEMETRY = [
    'VBOX_Lat_Min',
    'VBOX_Long_Minutes',
    'speed',
    'gear',
    'Steering_Angle',
    'pbrake_f',
    'pbrake_r',
    'aps',
    'nmot',
    'accx_can',
    'accy_can',
    'Laptrigger_lapdist_dls'
]

print(f"\n[1/5] Cargando datos... (esto tomará varios minutos)")

chunks = []
chunk_size = 2_000_000
max_records_target = 10_000_000

records_accumulated = 0

for i, chunk in enumerate(pd.read_csv(INPUT_FILE, chunksize=chunk_size)):
    print(f"  Chunk {i+1}: {len(chunk):,} registros", end="")

    # Filtrar TODA la telemetría
    chunk_filtered = chunk[chunk['telemetry_name'].isin(ALL_TELEMETRY)].copy()
    print(f" -> {len(chunk_filtered):,} filtrados", end="")

    # SIN downsampling
    chunk_sampled = chunk_filtered.copy()
    print(f" -> {len(chunk_sampled):,} incluidos")

    if len(chunk_sampled) > 0:
        chunks.append(chunk_sampled)
        records_accumulated += len(chunk_sampled)

    if records_accumulated >= max_records_target:
        print(f"  [INFO] Alcanzado objetivo de {max_records_target:,} registros")
        break

print(f"\n[2/5] Combinando {len(chunks)} chunks...")
df = pd.concat(chunks, ignore_index=True)
print(f"  Total registros: {len(df):,}")

print(f"\n[3/5] Procesando datos...")

# Convertir timestamp
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Solo 1 vehículo
vehicles = sorted(df['vehicle_id'].unique())[:1]
df = df[df['vehicle_id'].isin(vehicles)].copy()
print(f"  Vehículo seleccionado: {vehicles}")
print(f"  Registros del vehículo: {len(df):,}")

# Renombrar columnas
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

# Convertir GPS
for telem in ['latitude', 'longitude']:
    mask = df['telemetry_name'] == telem
    if mask.any():
        df.loc[mask, 'telemetry_value'] = df.loc[mask, 'telemetry_value'] / 60

print(f"\n[4/5] Detectando Yellow Flags...")

speed_data = df[df['telemetry_name'] == 'speed'].copy()
speed_data = speed_data.sort_values('timestamp')

speed_data['window'] = speed_data.groupby('vehicle_id')['timestamp'].transform(
    lambda x: (x - x.min()).dt.total_seconds() // 5
)

window_speed = speed_data.groupby(['vehicle_id', 'window']).agg({
    'telemetry_value': 'mean',
    'timestamp': 'first'
}).reset_index()

window_speed['is_yellow'] = window_speed['telemetry_value'] < 50

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

            if duration >= 30:
                yellow_flags.append({
                    'start': yellow_start.isoformat(),
                    'end': yellow_end.isoformat(),
                    'duration': duration
                })
            in_yellow = False

print(f"  [OK] {len(yellow_flags)} Yellow Flags detectados")
for i, yf in enumerate(yellow_flags[:10], 1):
    print(f"    {i}. Inicio: {yf['start'][:19]} | Duracion: {yf['duration']:.0f}s")
if len(yellow_flags) > 10:
    print(f"    ... y {len(yellow_flags) - 10} mas")

print(f"\n[5/5] Guardando archivo...")

df.to_parquet(
    OUTPUT_FILE,
    engine='pyarrow',
    compression='snappy',
    index=False
)

actual_size_mb = OUTPUT_FILE.stat().st_size / (1024**2)
duration_minutes = (df['timestamp'].max() - df['timestamp'].min()).total_seconds() / 60

print("\n" + "="*70)
print("RESUMEN - ROAD AMERICA R1")
print("="*70)
print(f"Registros totales:    {len(df):,}")
print(f"Vehiculos:            {len(df['vehicle_id'].unique())}")
print(f"Columnas telemetria:  {len(df['telemetry_name'].unique())}")
print(f"Duracion:             {duration_minutes:.1f} minutos ({duration_minutes/60:.1f} horas)")
print(f"Yellow Flags:         {len(yellow_flags)}")
print(f"Tamano archivo:       {actual_size_mb:.2f} MB")
print(f"Ubicacion:            {OUTPUT_FILE}")
print("="*70)
