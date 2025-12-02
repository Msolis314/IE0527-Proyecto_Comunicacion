#!/usr/bin/env python3
"""
Script de ejemplo para generar archivos .txt de prueba
para la funcionalidad de transmisión múltiple
"""

import pathlib
import random
from datetime import datetime

# Directorio donde se crearán los archivos
TEXTOS_DIR = pathlib.Path("Textos")

# Contenidos de ejemplo
EXAMPLE_CONTENTS = [
    """Este es un archivo de prueba #1.
Contiene información de ejemplo para demostrar
la funcionalidad de transmisión múltiple del sistema nRF24L01+.

Características del sistema:
- Velocidad: 32 KiB/s
- Compresión adaptativa
- FEC Reed-Solomon
- Transmisión optimizada

Fecha de creación: {}
""",
    
    """Documento de prueba #2
    
Este archivo contiene datos de sensores simulados:

Temperatura: {} °C
Humedad: {}%
Presión: {} hPa
Timestamp: {}

Sistema de monitoreo v1.0
""",
    
    """LOG DE SISTEMA - Archivo #3

[INFO] Inicialización del sistema
[INFO] Radio nRF24L01+ configurado correctamente
[INFO] Compresión: Habilitada
[INFO] FEC: Habilitado
[INFO] Velocidad: 2 MBPS
[INFO] Canal: 90
[WARN] Esperando conexión...
[INFO] Conexión establecida
[OK] Sistema operacional - {}
""",
    
    """=== CONFIGURACIÓN DEL DISPOSITIVO ===

Device ID: DEV-{:04d}
Firmware Version: 2.1.0
Hardware Version: 1.5

Network Configuration:
- RF Channel: 90
- Data Rate: 2 MBPS
- PA Level: MAX
- Auto-Retry: 15 attempts

Última actualización: {}
Estado: OPERACIONAL
""",
    
    """DATOS METEOROLÓGICOS - Estación {:03d}

Ubicación: San José, Costa Rica
Coordenadas: 9.93°N, 84.08°W
Altitud: 1150 msnm

Mediciones del día:
- Temp. Máxima: {} °C
- Temp. Mínima: {} °C
- Precipitación: {} mm
- Viento: {} km/h
- Radiación UV: {}

Fecha: {}
"""
]


def create_example_files(num_files: int = 5):
    """
    Crea archivos .txt de ejemplo en el directorio Textos/
    
    Args:
        num_files: Número de archivos a crear (default: 5)
    """
    # Crear directorio si no existe
    TEXTOS_DIR.mkdir(exist_ok=True)
    
    print(f"📁 Creando {num_files} archivos de ejemplo en '{TEXTOS_DIR}/'...\n")
    
    created_files = []
    
    for i in range(1, num_files + 1):
        # Seleccionar contenido aleatorio
        template = random.choice(EXAMPLE_CONTENTS)
        
        # Generar datos aleatorios
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        temp = random.randint(15, 35)
        humidity = random.randint(40, 90)
        pressure = random.randint(980, 1020)
        device_id = random.randint(1, 9999)
        station_id = random.randint(1, 999)
        rain = random.randint(0, 50)
        wind = random.randint(5, 30)
        uv = random.randint(1, 11)
        
        # Formatear contenido
        try:
            content = template.format(
                timestamp,
                temp,
                humidity,
                pressure,
                device_id,
                station_id,
                rain,
                wind,
                uv
            )
        except:
            content = template.format(timestamp)
        
        # Crear archivo
        filename = f"archivo_{i:02d}.txt"
        filepath = TEXTOS_DIR / filename
        
        filepath.write_text(content, encoding='utf-8')
        
        size = filepath.stat().st_size
        created_files.append((filename, size))
        
        print(f"  ✓ {filename} ({size} bytes)")
    
    print(f"\n✅ {len(created_files)} archivos creados exitosamente")
    print(f"📍 Ubicación: {TEXTOS_DIR.absolute()}")
    print(f"\n💡 Usa el modo 'tx-multi' para transmitir todos estos archivos:")
    print(f"   python3 main.py cualquier_archivo.pdf ./recibidos/ --mode tx-multi")
    print(f"\n🔘 O presiona el botón por 3+ segundos en modo idle\n")


def cleanup_files():
    """Elimina todos los archivos .txt del directorio Textos/"""
    if not TEXTOS_DIR.exists():
        print(f"⚠️  El directorio '{TEXTOS_DIR}' no existe")
        return
    
    txt_files = list(TEXTOS_DIR.glob("*.txt"))
    
    if not txt_files:
        print(f"ℹ️  No hay archivos .txt en '{TEXTOS_DIR}'")
        return
    
    print(f"🗑️  Eliminando {len(txt_files)} archivos...")
    
    for file in txt_files:
        file.unlink()
        print(f"  ✓ {file.name} eliminado")
    
    print(f"✅ Limpieza completada\n")


def list_files():
    """Lista todos los archivos .txt en el directorio Textos/"""
    if not TEXTOS_DIR.exists():
        print(f"⚠️  El directorio '{TEXTOS_DIR}' no existe")
        return
    
    txt_files = sorted(TEXTOS_DIR.glob("*.txt"))
    
    if not txt_files:
        print(f"ℹ️  No hay archivos .txt en '{TEXTOS_DIR}'")
        return
    
    print(f"\n📁 Archivos en '{TEXTOS_DIR}':")
    print("─" * 50)
    
    total_size = 0
    for i, file in enumerate(txt_files, 1):
        size = file.stat().st_size
        total_size += size
        print(f"  {i:2d}. {file.name:<30} {size:>6} bytes")
    
    print("─" * 50)
    print(f"Total: {len(txt_files)} archivos, {total_size} bytes\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Generador de archivos de prueba para transmisión múltiple',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Crear 5 archivos de prueba (default):
  python3 generar_archivos_prueba.py
  
  # Crear 10 archivos:
  python3 generar_archivos_prueba.py --num 10
  
  # Listar archivos existentes:
  python3 generar_archivos_prueba.py --list
  
  # Limpiar todos los archivos:
  python3 generar_archivos_prueba.py --clean
        """
    )
    
    parser.add_argument('--num', type=int, default=5,
                        help='Número de archivos a crear (default: 5)')
    parser.add_argument('--list', action='store_true',
                        help='Listar archivos existentes')
    parser.add_argument('--clean', action='store_true',
                        help='Eliminar todos los archivos .txt')
    
    args = parser.parse_args()
    
    if args.list:
        list_files()
    elif args.clean:
        cleanup_files()
    else:
        create_example_files(args.num)
