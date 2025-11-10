"""
Prepare Sample Telemetry Data for Simulator
============================================

Este script prepara archivos de telemetría de muestra
desde las carreras existentes para probar el simulador.

Uso:
    python prepare_sample_data.py
"""

import pandas as pd
from pathlib import Path
import sys

# Paths
SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parent.parent  # toyota-gr-racing-analytics
TOYOTA_PROJECT = PROJECT_ROOT.parent  # Toyota Project
CODE_ROOT = TOYOTA_PROJECT / "Code"
OUTPUT_DIR = PROJECT_ROOT / "simulator" / "sample_data"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("\n" + "="*70)
print("Preparando datos de muestra para el simulador")
print("="*70)
print(f"\nCODE_ROOT: {CODE_ROOT}")
print(f"OUTPUT_DIR: {OUTPUT_DIR}\n")

# ============================================================================
# OPCIONES DE CARRERAS DISPONIBLES
# ============================================================================

available_races = {
    '1': {
        'name': 'VIR Race 1 (con Yellow Flags)',
        'path': CODE_ROOT / 'virginia-international-raceway' / 'virginia-international-raceway' / 'VIR' / 'Race 1' / 'R1_vir_telemetry_data.csv',
        'output': 'vir_r1_telemetry.parquet'
    },
    '2': {
        'name': 'VIR Race 2 (con Yellow Flags)',
        'path': CODE_ROOT / 'virginia-international-raceway' / 'virginia-international-raceway' / 'VIR' / 'Race 2' / 'R2_vir_telemetry_data.csv',
        'output': 'vir_r2_telemetry.parquet'
    },
    '3': {
        'name': 'COTA Race 1',
        'path': CODE_ROOT / 'circuit-of-the-americas' / 'COTA' / 'Race 1' / 'R1_cota_telemetry_data.csv',
        'output': 'cota_r1_telemetry.parquet'
    },
    '4': {
        'name': 'Barber (sin Yellow Flags)',
        'path': CODE_ROOT / 'barber-motorsports-park' / 'barber' / 'R1_barber_telemetry_data.csv',
        'output': 'barber_r1_telemetry.parquet'
    }
}

print("Carreras disponibles:")
for key, race in available_races.items():
    print(f"  {key}. {race['name']}")

print("\nSelecciona una carrera (o 'all' para todas): ", end='')
selection = input().strip()

# ============================================================================
# PROCESAR CARRERAS
# ============================================================================

def process_race(race_info):
    """Procesa un archivo de telemetría y lo convierte a Parquet"""
    print(f"\nProcesando: {race_info['name']}")

    if not race_info['path'].exists():
        print(f"  [ERROR] No se encontró el archivo: {race_info['path']}")
        return False

    print(f"  Cargando CSV... (esto puede tomar unos minutos)")

    # Cargar en chunks para manejar archivos grandes
    chunks = []
    chunk_size = 500000

    try:
        for chunk in pd.read_csv(race_info['path'], chunksize=chunk_size):
            # Filtrar solo datos esenciales para el simulador ANTES de downsample
            essential_telemetry = ['latitude', 'longitude', 'speed', 'throttle', 'brake']
            chunk_filtered = chunk[chunk['telemetry_name'].isin(essential_telemetry)].copy()

            # Downsample moderado: 1 de cada 10 registros
            chunk_sampled = chunk_filtered.iloc[::10].copy()

            if len(chunk_sampled) > 0:
                chunks.append(chunk_sampled)
                print(f"    Procesado chunk: {len(chunk):,} -> {len(chunk_filtered):,} -> {len(chunk_sampled):,} registros")

            # Limitar a primeros 10 chunks para obtener más datos GPS
            if len(chunks) >= 10:
                print(f"    [INFO] Limitando a primeros 10 chunks para mejor performance")
                break

        df = pd.concat(chunks, ignore_index=True)

        print(f"  [OK] Datos cargados: {len(df):,} registros")

        # Validar columnas requeridas
        required_cols = ['timestamp', 'vehicle_id', 'telemetry_name', 'telemetry_value']
        missing_cols = [col for col in required_cols if col not in df.columns]

        if missing_cols:
            print(f"  [ERROR] Faltan columnas: {missing_cols}")
            return False

        # Convertir timestamp
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        # Filtrar solo primeros 2 vehículos para reducir tamaño
        unique_vehicles = sorted(df['vehicle_id'].unique())[:2]
        df = df[df['vehicle_id'].isin(unique_vehicles)].copy()
        print(f"  [INFO] Filtrando a {len(unique_vehicles)} vehículos: {unique_vehicles}")

        # Limitar a primeros 15 minutos de carrera (más tiempo para ver Yellow Flags)
        start_time = df['timestamp'].min()
        end_time = start_time + pd.Timedelta(minutes=15)
        df = df[df['timestamp'] <= end_time].copy()
        print(f"  [INFO] Limitando a primeros 15 minutos de carrera")

        # Verificar que tenemos datos GPS
        gps_data = df[df['telemetry_name'].isin(['latitude', 'longitude'])]
        print(f"  [INFO] Registros GPS: {len(gps_data)} ({len(gps_data)/len(df)*100:.1f}%)")

        # Guardar como Parquet (comprimido)
        output_file = OUTPUT_DIR / race_info['output']
        df.to_parquet(output_file, index=False, compression='snappy')

        file_size_mb = output_file.stat().st_size / (1024 * 1024)

        print(f"  [OK] Guardado: {output_file.name} ({file_size_mb:.1f} MB)")
        print(f"       Registros: {len(df):,}")
        print(f"       Vehículos: {df['vehicle_id'].nunique()}")
        print(f"       Duración: {(df['timestamp'].max() - df['timestamp'].min()).total_seconds():.0f}s")

        return True

    except Exception as e:
        print(f"  [ERROR] {e}")
        return False


# Procesar selección
if selection.lower() == 'all':
    print("\nProcesando todas las carreras...")
    for race_info in available_races.values():
        process_race(race_info)
elif selection in available_races:
    process_race(available_races[selection])
else:
    print(f"\n[ERROR] Selección inválida: {selection}")
    sys.exit(1)

# ============================================================================
# RESUMEN
# ============================================================================

print("\n" + "="*70)
print("COMPLETADO")
print("="*70)

output_files = list(OUTPUT_DIR.glob("*.parquet"))

if len(output_files) > 0:
    print(f"\nArchivos generados en: {OUTPUT_DIR}")
    for file in output_files:
        size_mb = file.stat().st_size / (1024 * 1024)
        print(f"  - {file.name} ({size_mb:.1f} MB)")

    print("\nPara usar en el simulador:")
    print("  1. python app.py")
    print("  2. Abrir http://127.0.0.1:8050")
    print(f"  3. Cargar uno de los archivos de: {OUTPUT_DIR.name}/")
else:
    print("\nNo se generaron archivos.")

print("="*70 + "\n")
