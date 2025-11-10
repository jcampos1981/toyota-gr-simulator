"""
Script para limpiar archivos temporales del disco C
"""
import os
import shutil
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

def get_size_mb(path):
    """Obtener tamaño de directorio en MB"""
    total = 0
    try:
        for entry in os.scandir(path):
            if entry.is_file(follow_symlinks=False):
                total += entry.stat().st_size
            elif entry.is_dir(follow_symlinks=False):
                total += get_size_mb(entry.path)
    except (PermissionError, FileNotFoundError, OSError):
        pass
    return total / (1024 * 1024)

def clean_directory(path, extensions=None, days_old=1):
    """
    Limpiar archivos antiguos de un directorio

    Args:
        path: Ruta del directorio
        extensions: Lista de extensiones a eliminar (None = todas)
        days_old: Eliminar archivos más antiguos que N días
    """
    deleted_count = 0
    freed_mb = 0
    cutoff_time = datetime.now() - timedelta(days=days_old)

    try:
        for root, dirs, files in os.walk(path):
            for filename in files:
                try:
                    filepath = os.path.join(root, filename)

                    # Verificar extensión si se especificó
                    if extensions:
                        if not any(filename.endswith(ext) for ext in extensions):
                            continue

                    # Verificar antigüedad
                    if os.path.getmtime(filepath) < cutoff_time.timestamp():
                        file_size = os.path.getsize(filepath) / (1024 * 1024)
                        os.remove(filepath)
                        deleted_count += 1
                        freed_mb += file_size
                except (PermissionError, FileNotFoundError, OSError):
                    continue
    except (PermissionError, FileNotFoundError, OSError):
        pass

    return deleted_count, freed_mb

def main():
    print("=" * 70)
    print("Limpieza de Disco C: - Toyota GR Racing Simulator")
    print("=" * 70)
    print()

    total_freed = 0

    # 1. Limpiar %TEMP%
    print("[1/4] Limpiando archivos temporales de Windows...")
    temp_dir = tempfile.gettempdir()
    size_before = get_size_mb(temp_dir)

    count, freed = clean_directory(
        temp_dir,
        extensions=['.tmp', '.temp', '.log', '.cache', '.bak'],
        days_old=1
    )
    print(f"  [OK] {count} archivos eliminados")
    print(f"  [OK] {freed:.1f} MB liberados")
    total_freed += freed
    print()

    # 2. Limpiar C:\Windows\Temp
    print("[2/4] Limpiando archivos temporales del sistema...")
    windows_temp = Path("C:/Windows/Temp")
    if windows_temp.exists():
        count, freed = clean_directory(
            str(windows_temp),
            extensions=['.tmp', '.temp', '.log'],
            days_old=1
        )
        print(f"  [OK] {count} archivos eliminados")
        print(f"  [OK] {freed:.1f} MB liberados")
        total_freed += freed
    else:
        print("  [SKIP] No accesible (requiere permisos)")
    print()

    # 3. Limpiar caché de pip
    print("[3/4] Limpiando cache de pip...")
    pip_cache = Path(os.path.expanduser("~/.cache/pip"))
    if pip_cache.exists():
        size_before = get_size_mb(str(pip_cache))
        try:
            shutil.rmtree(pip_cache)
            print(f"  [OK] {size_before:.1f} MB liberados")
            total_freed += size_before
        except (PermissionError, OSError) as e:
            print(f"  [SKIP] No se pudo eliminar: {e}")
    else:
        print("  [OK] No hay cache de pip")
    print()

    # 4. Limpiar archivos __pycache__
    print("[4/4] Limpiando archivos __pycache__...")
    count = 0
    freed = 0
    for root, dirs, files in os.walk("H:/Toyota Project"):
        if '__pycache__' in dirs:
            pycache_path = os.path.join(root, '__pycache__')
            try:
                size = get_size_mb(pycache_path)
                shutil.rmtree(pycache_path)
                count += 1
                freed += size
            except (PermissionError, OSError):
                pass
    print(f"  [OK] {count} directorios eliminados")
    print(f"  [OK] {freed:.1f} MB liberados")
    total_freed += freed
    print()

    # Resumen
    print("=" * 70)
    print(f"TOTAL LIBERADO: {total_freed:.1f} MB ({total_freed/1024:.2f} GB)")
    print("=" * 70)
    print()

    # Mostrar espacio disponible ahora
    print("Espacio en disco C:")
    try:
        import psutil
        disk = psutil.disk_usage('C:/')
        print(f"  Total: {disk.total / (1024**3):.1f} GB")
        print(f"  Usado: {disk.used / (1024**3):.1f} GB")
        print(f"  Libre: {disk.free / (1024**3):.1f} GB ({disk.percent}%)")
    except ImportError:
        print("  (instalar psutil para ver detalles)")

    print()

if __name__ == '__main__':
    main()
