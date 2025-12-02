#!/usr/bin/env python3
"""
Sistema bidireccional de transferencia de archivos para nRF24L01+
Punto de entrada principal

Uso:
    python3 main.py <archivo_a_enviar> <directorio_recepcion>
"""

import sys
import time
import pathlib

# Importar módulos del proyecto
from radio_config import initialize_radio
from hardware import LEDController, ButtonController, SystemState, GPIO
from transmitter import transmit_file, transmit_multiple_files
from receiver import receive_file
from constants import (
    FRAME_SIZE, FEC_SYMBOLS, BURST_SIZE, INTER_PACKET_DELAY
)
from fec import is_fec_available


def print_banner():
    """Imprime el banner de información del sistema"""
    print("="*70)
    print("SISTEMA DE TRANSFERENCIA BIDIRECCIONAL nRF24L01+")
    print("="*70)
    print("\nOPTIMIZACIONES ACTIVAS:")
    print(f"  Payload: {FRAME_SIZE} bytes (límite nRF24)")
    
    if is_fec_available():
        print(f"   FEC Reed-Solomon: {FEC_SYMBOLS} símbolos (6+22+4=32)")
    else:
        print("  FEC deshabilitado (instalar: pip install reedsolo)")
    
    print("  ✓ Compresión adaptativa: zlib, bz2, lzma")
    print("  ✓ Data rate: 2 MBPS")
    print(f"  ✓ Modo ráfaga: {BURST_SIZE} paquetes/burst")
    print(f"  ✓ Delay ultra-bajo: {INTER_PACKET_DELAY*1000:.1f}ms entre paquetes")
    
    print("\n📡 ESTADOS LED:")
    print("  🟢 Verde parpadeando: Sistema en espera (Idle)")
    print("  🟡 Amarillo fijo: Transferencia en progreso")
    print("  🔴 Rojo parpadeando: Transferencia completada")
    print("  🟡🔴 Amarillo+Rojo: Error en transferencia")
    
    print("\n🎮 CONTROL:")
    print("  • Pulsación CORTA (<1s): Modo TRANSMISOR (TX) - archivo único")
    print("  • Pulsación MEDIA (1-3s): Modo RECEPTOR (RX)")
    print("  • Pulsación LARGA (≥3s): Modo TX-MULTI - transmitir todos los .txt")
    print("  • Presione Ctrl+C para salir del programa")
    print("\n" + "="*70 + "\n")


def main():
    """Función principal del programa"""
    
    import argparse
    
    # Parser de argumentos
    parser = argparse.ArgumentParser(
        description='Sistema bidireccional de transferencia de archivos nRF24L01+',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Modo normal (espera botón):
  python3 main.py documento.pdf ./recibidos/
  
  # Iniciar directamente en modo TRANSMISOR:
  python3 main.py documento.pdf ./recibidos/ --mode tx
  
  # Iniciar directamente en modo RECEPTOR:
  python3 main.py documento.pdf ./recibidos/ --mode rx
  
  # Iniciar directamente en modo TRANSMISIÓN MÚLTIPLE:
  python3 main.py documento.pdf ./recibidos/ --mode tx-multi
  
  # Especificar directorio de textos personalizado:
  python3 main.py documento.pdf ./recibidos/ --textos-dir ./MisTextos
        """
    )
    
    parser.add_argument('archivo_a_enviar', 
                        help='Archivo que se transmitirá')
    parser.add_argument('directorio_recepcion', 
                        help='Carpeta donde se guardarán archivos recibidos')
    parser.add_argument('--mode', 
                        choices=['tx', 'rx', 'idle', 'tx-multi'],
                        default='idle',
                        help='Modo inicial: tx (transmisor), rx (receptor), tx-multi (transmitir múltiples), idle (esperar botón)')
    parser.add_argument('--textos-dir',
                        default='Textos',
                        help='Directorio con archivos .txt para transmisión múltiple (default: Textos)')
    
    args = parser.parse_args()
    
    file_path = pathlib.Path(args.archivo_a_enviar)
    dest_dir = pathlib.Path(args.directorio_recepcion)
    textos_dir = pathlib.Path(args.textos_dir)

    # Validar archivo y directorio
    if not file_path.is_file():
        print(f" Error: '{file_path}' no es un archivo válido")
        sys.exit(1)
    
    if not dest_dir.is_dir():
        print(f" Error: '{dest_dir}' no es un directorio válido")
        print(f"   Creando directorio...")
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
            print(f"    Directorio creado: {dest_dir.absolute()}")
        except Exception as e:
            print(f"    No se pudo crear el directorio: {e}")
            sys.exit(1)
    
    # Crear directorio de textos si no existe
    if not textos_dir.exists():
        print(f"Creando directorio de textos: {textos_dir}")
        try:
            textos_dir.mkdir(parents=True, exist_ok=True)
            print(f"    Directorio creado: {textos_dir.absolute()}")
        except Exception as e:
            print(f"   No se pudo crear el directorio: {e}")
            print(f"   La transmisión múltiple no estará disponible")

    # Inicializar radio
    try:
        radio = initialize_radio()
    except RuntimeError as e:
        print(f"\n{e}")
        print("\n Verifica:")
        print("  1. Conexiones del nRF24L01+ (VCC a 3.3V, NO 5V)")
        print("  2. SPI habilitado: sudo raspi-config → Interface → SPI")
        print("  3. Permisos: sudo usermod -a -G spi,gpio $USER")
        sys.exit(1)

    # Inicializar controladores de hardware
    led_controller = LEDController()
    mode = {'current': args.mode}  # Usar modo inicial del argumento

    def short_press():
        """Callback para pulsación corta -> TX"""
        if mode['current'] == 'idle':
            mode['current'] = 'tx'
            print("\n BOTÓN CORTO → Iniciando TRANSMISIÓN (TX)")

    def medium_press():
        """Callback para pulsación media -> RX"""
        if mode['current'] == 'idle':
            mode['current'] = 'rx'
            print("\n BOTÓN MEDIO → Iniciando RECEPCIÓN (RX)")

    def long_press():
        """Callback para pulsación larga -> TX-MULTI"""
        if mode['current'] == 'idle':
            mode['current'] = 'tx-multi'
            print("\n BOTÓN LARGO → Iniciando TRANSMISIÓN MÚLTIPLE (TX-MULTI)")

    button_controller = ButtonController(short_press, medium_press, long_press)

    # Mostrar banner
    print_banner()
    
    print(f" Archivo a transmitir: {file_path.name}")
    print(f"Directorio de recepción: {dest_dir.absolute()}")
    print(f"Directorio de textos: {textos_dir.absolute()}")
    
    if args.mode == 'idle':
        print(f"\n Sistema en espera - Presione el botón para comenzar\n")
    elif args.mode == 'tx':
        print(f"\n Modo inicial: TRANSMISOR - Iniciando automáticamente...\n")
    elif args.mode == 'rx':
        print(f"\n Modo inicial: RECEPTOR - Iniciando automáticamente...\n")
    elif args.mode == 'tx-multi':
        print(f"\n Modo inicial: TRANSMISIÓN MÚLTIPLE - Iniciando automáticamente...\n")

    # Bucle principal
    try:
        while True:
            if mode['current'] == 'tx':
                print("\n" + "▶"*35)
                print("MODO TRANSMISOR ACTIVADO")
                print("▶"*35 + "\n")
                
                transmit_file(radio, file_path, led_controller)
                
                time.sleep(3)
                mode['current'] = 'idle'
                led_controller.set_state(SystemState.IDLE)
                print("\n💤 Idle - Presione el botón para nueva operación\n")
                
            elif mode['current'] == 'tx-multi':
                print("\n" + "▶"*35)
                print("MODO TRANSMISIÓN MÚLTIPLE ACTIVADO")
                print("▶"*35 + "\n")
                
                transmit_multiple_files(radio, textos_dir, led_controller)
                
                time.sleep(3)
                mode['current'] = 'idle'
                led_controller.set_state(SystemState.IDLE)
                print("\n Idle - Presione el botón para nueva operación\n")
                
            elif mode['current'] == 'rx':
                print("\n" + "◀"*35)
                print("MODO RECEPTOR ACTIVADO")
                print("◀"*35 + "\n")
                
                receive_file(radio, dest_dir, led_controller)
                
                time.sleep(3)
                mode['current'] = 'idle'
                led_controller.set_state(SystemState.IDLE)
                print("\n Idle - Presione el botón para cambiar a TX\n")
                
            else:
                # Estado idle: esperar entrada del botón
                time.sleep(0.1)
                
    except KeyboardInterrupt:
        print("\n\n Sistema detenido por el usuario")
        
    finally:
        # Limpieza
        print("\n Limpiando recursos...")
        led_controller.cleanup()
        if GPIO:
            GPIO.cleanup()
        print(" Limpieza completada\n")


if __name__ == "__main__":
    main()
