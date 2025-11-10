"""
Limpieza agresiva de archivos temporales en disco C
"""
import os
import shutil
import tempfile
from pathlib import Path
import psutil

def remove_tree(path):
    """Eliminar directorio completo"""
    try:
        shutil.rmtree(path)
        return True
    except (PermissionError, OSError, FileNotFoundError):
        return False

def get_dir_size_gb(path):
    """Obtener tamaño de directorio en GB"""
    total = 0
    try:
        for entry in os.scandir(path):
            if entry.is_file(follow_symlinks=False):
                total += entry.stat().st_size
            elif entry.is_dir(follow_symlinks=False):
                total += get_dir_size_gb(entry.path) * (1024**3)
    except (PermissionError, FileNotFoundError, OSError):
        pass
    return total / (1024**3)

def main():
    print("=" * 70)
    print("LIMPIEZA AGRESIVA - Disco C:")
    print("=" * 70)
    print()

    # Estado inicial
    disk_before = psutil.disk_usage('C:/')
    print(f"Espacio libre ANTES: {disk_before.free/(1024**3):.2f} GB")
    print()

    total_freed = 0

    # 1. Limpiar TODOS los archivos temporales de usuario
    print("[1/6] Limpiando %TEMP% completo...")
    temp_dir = Path(tempfile.gettempdir())
    if temp_dir.exists():
        count = 0
        for item in temp_dir.iterdir():
            try:
                if item.is_file():
                    size = item.stat().st_size / (1024**3)
                    os.remove(item)
                    total_freed += size
                    count += 1
                elif item.is_dir():
                    size = get_dir_size_gb(str(item))
                    if remove_tree(str(item)):
                        total_freed += size
                        count += 1
            except (PermissionError, OSError):
                continue
        print(f"  [OK] {count} items eliminados")
    print()

    # 2. Limpiar caché de navegadores
    print("[2/6] Limpiando cache de navegadores...")
    appdata = Path(os.getenv('LOCALAPPDATA'))
    browser_caches = [
        appdata / 'Google' / 'Chrome' / 'User Data' / 'Default' / 'Cache',
        appdata / 'Microsoft' / 'Edge' / 'User Data' / 'Default' / 'Cache',
        appdata / 'Mozilla' / 'Firefox' / 'Profiles',
    ]

    count = 0
    for cache_path in browser_caches:
        if cache_path.exists():
            if 'Firefox' in str(cache_path):
                # Limpiar solo carpetas cache de Firefox
                for profile in cache_path.iterdir():
                    cache_dir = profile / 'cache2'
                    if cache_dir.exists() and remove_tree(str(cache_dir)):
                        count += 1
            else:
                if remove_tree(str(cache_path)):
                    count += 1
    print(f"  [OK] {count} caches eliminados")
    print()

    # 3. Limpiar Windows Update cache (mas agresivo)
    print("[3/6] Limpiando Windows Update cache...")
    update_cache = Path("C:/Windows/SoftwareDistribution/Download")
    if update_cache.exists():
        count = 0
        for item in update_cache.iterdir():
            if remove_tree(str(item)) if item.is_dir() else True:
                try:
                    if item.is_file():
                        os.remove(item)
                    count += 1
                except:
                    pass
        print(f"  [OK] {count} items eliminados")
    else:
        print("  [SKIP] No accesible")
    print()

    # 4. Limpiar logs antiguos
    print("[4/6] Limpiando archivos .log...")
    count = 0
    for drive_letter in ['C']:
        for root, dirs, files in os.walk(f"{drive_letter}:/Users"):
            for file in files:
                if file.endswith('.log'):
                    try:
                        filepath = os.path.join(root, file)
                        size = os.path.getsize(filepath) / (1024**3)
                        os.remove(filepath)
                        total_freed += size
                        count += 1
                    except (PermissionError, OSError):
                        pass
    print(f"  [OK] {count} archivos .log eliminados")
    print()

    # 5. Limpiar archivos .tmp grandes
    print("[5/6] Limpiando archivos .tmp grandes (>10MB)...")
    count = 0
    for root, dirs, files in os.walk("C:/"):
        # Evitar directorios del sistema
        if any(x in root.lower() for x in ['windows', 'program files', 'system32']):
            continue

        for file in files:
            if file.endswith(('.tmp', '.temp')):
                try:
                    filepath = os.path.join(root, file)
                    size = os.path.getsize(filepath) / (1024**2)  # MB
                    if size > 10:  # Mayor a 10 MB
                        os.remove(filepath)
                        total_freed += size / 1024  # GB
                        count += 1
                except (PermissionError, OSError):
                    pass
    print(f"  [OK] {count} archivos grandes eliminados")
    print()

    # 6. Limpiar Recycle Bin
    print("[6/6] Vaciando Papelera de reciclaje...")
    recycle_bin = Path("C:/$Recycle.Bin")
    if recycle_bin.exists():
        count = 0
        for item in recycle_bin.iterdir():
            if remove_tree(str(item)) if item.is_dir() else True:
                try:
                    if item.is_file():
                        os.remove(item)
                    count += 1
                except:
                    pass
        print(f"  [OK] Papelera vaciada")
    else:
        print("  [SKIP] No accesible")
    print()

    # Estado final
    disk_after = psutil.disk_usage('C:/')
    actual_freed = (disk_after.free - disk_before.free) / (1024**3)

    print("=" * 70)
    print(f"ESPACIO LIBERADO: {actual_freed:.2f} GB")
    print("=" * 70)
    print()
    print(f"Espacio libre ANTES:  {disk_before.free/(1024**3):.2f} GB")
    print(f"Espacio libre AHORA:  {disk_after.free/(1024**3):.2f} GB")
    print(f"Porcentaje usado:     {disk_after.percent}%")
    print()

if __name__ == '__main__':
    main()
