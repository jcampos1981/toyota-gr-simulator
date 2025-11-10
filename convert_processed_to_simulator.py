"""
Convertir archivos procesados (wide format) a formato simulador (long format)
"""

import pandas as pd
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parent.parent  # toyota-gr-racing-analytics
INPUT_FILE = PROJECT_ROOT / "data" / "processed" / "telemetry_with_corners_R2.parquet"
OUTPUT_FILE = PROJECT_ROOT / "simulator" / "sample_data" / "barber_r2_with_gps.parquet"

print(f"PROJECT_ROOT: {PROJECT_ROOT}")
print(f"INPUT_FILE: {INPUT_FILE}")
print(f"File exists: {INPUT_FILE.exists()}")

print("\n" + "="*70)
print("Convirtiendo archivo procesado a formato simulador")
print("="*70)

# Cargar datos
print(f"\nCargando: {INPUT_FILE.name}")
df = pd.read_parquet(INPUT_FILE)
print(f"Registros originales: {len(df):,}")

# NO limitar - usar todos los datos disponibles para generar archivo más grande
# df = df.head(10000)
print(f"Usando todos los registros: {len(df):,}")

# Convertir VBOX_Lat_Min y VBOX_Long_Minutes a grados decimales
df['latitude'] = df['VBOX_Lat_Min'] / 60  # Convertir minutos a grados
df['longitude'] = df['VBOX_Long_Minutes'] / 60

# Downsample: tomar 1 de cada 3 registros para reducir tamaño
df = df.iloc[::3].copy()
print(f"Después de downsample (1/3): {len(df):,} registros")

# Seleccionar columnas esenciales con más telemetría
essential_cols = {
    'latitude': 'latitude',
    'longitude': 'longitude',
    'speed': 'speed',
    'gear': 'gear',
    'nmot': 'nmot',
    'Steering_Angle': 'throttle',  # Usar steering como proxy de throttle
    'pbrake_f': 'brake'  # Usar freno delantero
}

# Convertir a formato long
records = []
vehicle_id = "GR86-FASTEST"

for idx, row in df.iterrows():
    timestamp = row['timestamp']

    for col_name, tel_name in essential_cols.items():
        if col_name in df.columns and pd.notna(row[col_name]):
            records.append({
                'timestamp': timestamp,
                'vehicle_id': vehicle_id,
                'telemetry_name': tel_name,
                'telemetry_value': float(row[col_name])
            })

# Crear DataFrame long
df_long = pd.DataFrame(records)
print(f"\nRegistros en formato long: {len(df_long):,}")
print(f"Telemetry types: {df_long['telemetry_name'].unique()}")

# Verificar GPS
gps_count = len(df_long[df_long['telemetry_name'].isin(['latitude', 'longitude'])])
print(f"Registros GPS: {gps_count} ({gps_count/len(df_long)*100:.1f}%)")

# Guardar
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
df_long.to_parquet(OUTPUT_FILE, index=False, compression='snappy')

file_size_mb = OUTPUT_FILE.stat().st_size / (1024 * 1024)
print(f"\n[OK] Guardado: {OUTPUT_FILE.name} ({file_size_mb:.1f} MB)")

duration = (df_long['timestamp'].max() - df_long['timestamp'].min()).total_seconds()
print(f"     Duración: {duration:.0f}s ({duration/60:.1f} min)")

print("="*70)
print("LISTO! Ahora carga este archivo en el simulador:")
print(f"  {OUTPUT_FILE}")
print("="*70 + "\n")
