"""
Crear archivo de muestra GRANDE (5-10MB) con GPS para el simulador
==================================================================
"""

import pandas as pd
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parent.parent
TOYOTA_PROJECT = PROJECT_ROOT.parent
CODE_ROOT = TOYOTA_PROJECT / "Code"

INPUT_FILE = CODE_ROOT / "barber-motorsports-park" / "barber" / "R2_barber_telemetry_data.csv"
OUTPUT_FILE = PROJECT_ROOT / "simulator" / "sample_data" / "barber_r2_large.parquet"

print("\n" + "="*70)
print("Creando archivo de muestra GRANDE con GPS")
print("="*70)
print(f"\nInput: {INPUT_FILE}")
print(f"Output: {OUTPUT_FILE}")

# Telemetría esencial para el simulador
ESSENTIAL_TELEMETRY = ['VBOX_Lat_Min', 'VBOX_Long_Minutes', 'speed', 'gear', 'Steering_Angle', 'pbrake_f']

print(f"\n[1/4] Cargando datos con chunks...")

chunks = []
chunk_size = 1_000_000
max_chunks = 15  # ~15M registros raw = objetivo ~500K después de filtros

for i, chunk in enumerate(pd.read_csv(INPUT_FILE, chunksize=chunk_size)):
    print(f"  Chunk {i+1}: {len(chunk):,} registros", end="")

    # Filtrar solo telemetría esencial
    chunk_filtered = chunk[chunk['telemetry_name'].isin(ESSENTIAL_TELEMETRY)].copy()
    print(f" -> {len(chunk_filtered):,} filtrados", end="")

    # Downsample agresivo: 1 de cada 15 registros
    chunk_sampled = chunk_filtered.iloc[::15].copy()
    print(f" -> {len(chunk_sampled):,} downsampled")

    if len(chunk_sampled) > 0:
        chunks.append(chunk_sampled)

    if len(chunks) >= max_chunks:
        print(f"  [INFO] Limitando a {max_chunks} chunks")
        break

print(f"\n[2/4] Combinando chunks...")
df = pd.concat(chunks, ignore_index=True)
print(f"  Total registros: {len(df):,}")

print(f"\n[3/4] Procesando datos...")

# Convertir timestamp
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Filtrar solo primer vehículo
first_vehicle = df['vehicle_id'].iloc[0]
df = df[df['vehicle_id'] == first_vehicle].copy()
print(f"  Vehículo seleccionado: {first_vehicle}")
print(f"  Registros del vehículo: {len(df):,}")

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

# Seleccionar solo columnas necesarias
df = df[['timestamp', 'vehicle_id', 'telemetry_name', 'telemetry_value']].copy()

print(f"\n[4/4] Guardando archivo...")
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
df.to_parquet(OUTPUT_FILE, index=False, compression='snappy')

file_size_mb = OUTPUT_FILE.stat().st_size / (1024 * 1024)
duration = (df['timestamp'].max() - df['timestamp'].min()).total_seconds()

print(f"\n" + "="*70)
print(f"✓ COMPLETADO")
print(f"="*70)
print(f"Archivo: {OUTPUT_FILE.name}")
print(f"Tamaño: {file_size_mb:.1f} MB")
print(f"Registros: {len(df):,}")
print(f"Duración: {duration:.0f}s ({duration/60:.1f} min)")
print(f"Telemetría: {sorted(df['telemetry_name'].unique())}")
print(f"\nCarga este archivo en el simulador: http://127.0.0.1:8050")
print(f"="*70 + "\n")
