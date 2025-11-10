"""
Limpieza rápida y efectiva del disco C
"""
import os
import shutil
import tempfile
from pathlib import Path
import psutil

def main():
    print("=" * 70)
    print("LIMPIEZA RAPIDA - Disco C:")
    print("=" * 70)
    print()

    # Estado inicial
    disk_before = psutil.disk_usage('C:/')
    print(f"Espacio libre ANTES: {disk_before.free/(1024**3):.2f} GB")
    print()

    # 1. Limpiar %TEMP%
    print("[1/5] Limpiando %TEMP%...")
    temp_dir = Path(tempfile.gettempdir())
    count = 0
    if temp_dir.exists():
        for item in temp_dir.iterdir():
            try:
                if item.is_file():
                    os.remove(item)
                    count += 1
                elif item.is_dir():
                    shutil.rmtree(item)
                    count += 1
            except (PermissionError, OSError):
                pass
    print(f"  [OK] {count} items eliminados de %TEMP%")
    print()

    # 2. Limpiar caché de Chrome
    print("[2/5] Limpiando cache de Chrome...")
    chrome_cache = Path(os.getenv('LOCALAPPDATA')) / 'Google' / 'Chrome' / 'User Data' / 'Default' / 'Cache'
    if chrome_cache.exists():
        try:
            shutil.rmtree(chrome_cache)
            print("  [OK] Cache de Chrome eliminado")
        except (PermissionError, OSError):
            print("  [SKIP] No se pudo eliminar (cerrar Chrome primero)")
    else:
        print("  [SKIP] No existe")
    print()

    # 3. Limpiar archivos temporales de Dash/Flask
    print("[3/5] Limpiando archivos de Dash/Flask...")
    appdata = Path(os.getenv('APPDATA'))
    localappdata = Path(os.getenv('LOCALAPPDATA'))

    flask_dirs = [
        appdata / 'flask',
        localappdata / 'pip',
        localappdata / 'matplotlib',
    ]

    count = 0
    for flask_dir in flask_dirs:
        if flask_dir.exists():
            try:
                shutil.rmtree(flask_dir)
                count += 1
            except (PermissionError, OSError):
                pass
    print(f"  [OK] {count} directorios de cache eliminados")
    print()

    # 4. Limpiar archivos .pyc y __pycache__ en C:
    print("[4/5] Limpiando archivos .pyc en disco C...")
    count_pyc = 0
    count_pycache = 0

    # Solo limpiar directorios de usuario, no todo C:
    user_dirs = [
        Path(os.getenv('USERPROFILE')),
        Path(os.getenv('APPDATA')),
        Path(os.getenv('LOCALAPPDATA')),
    ]

    for user_dir in user_dirs:
        if not user_dir.exists():
            continue

        for root, dirs, files in os.walk(user_dir):
            # Limpiar __pycache__
            if '__pycache__' in dirs:
                pycache_path = Path(root) / '__pycache__'
                try:
                    shutil.rmtree(pycache_path)
                    count_pycache += 1
                except (PermissionError, OSError):
                    pass

            # Limpiar .pyc
            for file in files:
                if file.endswith('.pyc'):
                    try:
                        os.remove(Path(root) / file)
                        count_pyc += 1
                    except (PermissionError, OSError):
                        pass

    print(f"  [OK] {count_pyc} archivos .pyc eliminados")
    print(f"  [OK] {count_pycache} directorios __pycache__ eliminados")
    print()

    # 5. Limpiar archivos grandes temporales
    print("[5/5] Limpiando archivos .tmp grandes en %TEMP%...")
    temp_dir = Path(tempfile.gettempdir())
    count = 0
    freed_mb = 0

    if temp_dir.exists():
        for item in temp_dir.rglob('*.tmp'):
            try:
                if item.is_file():
                    size_mb = item.stat().st_size / (1024**2)
                    if size_mb > 1:  # Mayor a 1 MB
                        os.remove(item)
                        count += 1
                        freed_mb += size_mb
            except (PermissionError, OSError):
                pass

    print(f"  [OK] {count} archivos .tmp eliminados ({freed_mb:.1f} MB)")
    print()

    # Estado final
    disk_after = psutil.disk_usage('C:/')
    freed_gb = (disk_after.free - disk_before.free) / (1024**3)

    print("=" * 70)
    print(f"ESPACIO LIBERADO: {freed_gb:.2f} GB")
    print("=" * 70)
    print()
    print(f"Espacio libre ANTES:  {disk_before.free/(1024**3):.2f} GB")
    print(f"Espacio libre AHORA:  {disk_after.free/(1024**3):.2f} GB")
    print(f"Porcentaje usado:     {disk_after.percent:.1f}%")
    print()

if __name__ == '__main__':
    main()
