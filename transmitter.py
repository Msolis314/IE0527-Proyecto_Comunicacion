"""
Lógica de transmisión de archivos (OPTIMIZADO)
Eliminados reintentos manuales - confía en auto-retransmit del hardware nRF24
"""

import time
import random
import pathlib
from pyrf24 import RF24
from constants import (
    ADDR_A, ADDR_B, MAX_ROUNDS,
    BURST_SIZE, INTER_PACKET_DELAY, EFFECTIVE_DATA_BYTES, DATA_BYTES,
    COMPRESS_NAMES
)
from compression import adaptive_compress
from frame_handler import (
    calculate_file_hash, build_frame, parse_ack
)
from fec import is_fec_available
from hardware import LEDController, SystemState


def split_file(file_path: pathlib.Path, use_fec: bool = True) -> tuple:
    """
    Lee, comprime y divide un archivo en chunks.
    
    Args:
        file_path: Ruta al archivo a transmitir
        use_fec: Si usar FEC (afecta tamaño de chunks)
        
    Returns:
        tuple: (chunks, compress_mode, original_size, final_size, file_hash)
    """
    data = file_path.read_bytes()
    original_size = len(data)
    file_hash = calculate_file_hash(data)
    
    # Comprimir de forma adaptativa
    compressed, compress_mode, ratio = adaptive_compress(data)
    final_size = len(compressed)
    
    # Dividir en chunks según FEC
    chunk_size = EFFECTIVE_DATA_BYTES if (use_fec and is_fec_available()) else DATA_BYTES
    chunks = [compressed[i:i+chunk_size] for i in range(0, len(compressed), chunk_size)]
    
    return chunks, compress_mode, original_size, final_size, file_hash


def transmit_multiple_files(radio: RF24, directory: pathlib.Path,
                           led_controller: LEDController) -> dict:
    """
    Transmite múltiples archivos .txt desde un directorio.
    
    Args:
        radio: Objeto RF24 inicializado
        directory: Directorio con archivos .txt
        led_controller: Controlador de LEDs
        
    Returns:
        dict: Estadísticas de transmisión {exitosos, fallidos, total}
    """
    print(f"\n{'='*50}")
    print("TRANSMISIÓN MÚLTIPLE DE ARCHIVOS")
    print(f"{'='*50}")
    print(f"Directorio: {directory.absolute()}\n")
    
    # Buscar archivos .txt
    txt_files = sorted(directory.glob("*.txt"))
    
    if not txt_files:
        print(f"⚠ No se encontraron archivos .txt en {directory}")
        return {'exitosos': 0, 'fallidos': 0, 'total': 0}
    
    print(f" Archivos encontrados: {len(txt_files)}")
    for i, f in enumerate(txt_files, 1):
        print(f"  {i}. {f.name} ({f.stat().st_size} bytes)")
    
    print(f"\n{'='*50}\n")
    
    stats = {'exitosos': 0, 'fallidos': 0, 'total': len(txt_files)}
    
    # Transmitir cada archivo
    for i, file_path in enumerate(txt_files, 1):
        print(f"\n📤 Transmitiendo archivo {i}/{len(txt_files)}: {file_path.name}")
        print(f"{'─'*50}")
        
        success = transmit_file(radio, file_path, led_controller)
        
        if success:
            stats['exitosos'] += 1
            print(f"✓ {file_path.name} transmitido exitosamente")
        else:
            stats['fallidos'] += 1
            print(f"✗ Error al transmitir {file_path.name}")
        
        # Pequeña pausa entre archivos
        if i < len(txt_files):
            print("\n⏸ Pausa de 2 segundos antes del siguiente archivo...")
            time.sleep(2)
    
    # Resumen final
    print(f"\n{'='*50}")
    print("RESUMEN DE TRANSMISIÓN MÚLTIPLE")
    print(f"{'='*50}")
    print(f"✓ Exitosos: {stats['exitosos']}/{stats['total']}")
    print(f"✗ Fallidos: {stats['fallidos']}/{stats['total']}")
    print(f"Tasa de éxito: {(stats['exitosos']/stats['total']*100):.1f}%")
    print(f"{'='*50}\n")
    
    return stats


def transmit_file(radio: RF24, file_path: pathlib.Path, 
                  led_controller: LEDController) -> bool:
    """
    Transmite un archivo completo usando nRF24L01+.
    
    Args:
        radio: Objeto RF24 inicializado
        file_path: Ruta al archivo a transmitir
        led_controller: Controlador de LEDs
        
    Returns:
        bool: True si la transmisión fue exitosa, False en caso contrario
    """
    print("\n[ MODO TRANSMISOR ]")
    led_controller.set_state(SystemState.TX_ACTIVE)
    
    try:
        # Configurar pipes
        radio.open_rx_pipe(1, ADDR_B)
        radio.stop_listening()
        radio.open_tx_pipe(ADDR_A)
        radio.set_retries(5, 5)

        file_id = random.randint(0, 65535)
        
        print(f"\n{'='*50}")
        print("MODO TRANSMISOR (OPTIMIZADO)")
        print(f"{'='*50}")
        print(f"Archivo: {file_path.name}")
        print(f"File ID: {file_id}")
        print(f"Tamaño original: {file_path.stat().st_size} bytes")

        # Preparar archivo
        start_prep = time.time()
        chunks, compress_mode, original_size, final_size, file_hash = split_file(
            file_path, use_fec=is_fec_available()
        )
        prep_time = time.time() - start_prep

        total_packets = len(chunks)
        chunk_size = EFFECTIVE_DATA_BYTES if is_fec_available() else DATA_BYTES

        print(f"Tamaño procesado: {final_size} bytes")
        print(f"Compresión: {COMPRESS_NAMES.get(compress_mode, 'unknown')}")
        print(f"Total paquetes: {total_packets}")
        print(f"Bytes por paquete: {chunk_size}")
        print(f"FEC: {'Habilitado' if is_fec_available() else 'Deshabilitado'}")
        print(f"Hash (4B): {file_hash.hex()}")
        print(f"Tiempo preparación: {prep_time:.3f}s")

        pending = set(range(total_packets))
        sent_count = 0
        success_count = 0
        start_time = time.time()
        burst_stats = {'sent': 0, 'ack': 0, 'fail': 0}

        # Bucle principal de transmisión
        for round_num in range(MAX_ROUNDS):
            if not pending:
                print("✓ Todos los paquetes confirmados!")
                break

            print(f"\n--- Ronda {round_num + 1} ---")
            print(f"Pendientes: {len(pending)}")
            pending_list = sorted(pending)

            # Transmitir en ráfagas
            for burst_start in range(0, len(pending_list), BURST_SIZE):
                burst_end = min(burst_start + BURST_SIZE, len(pending_list))
                burst = pending_list[burst_start:burst_end]

                for seq_id in burst:
                    is_last = (seq_id == total_packets - 1)
                    frame = build_frame(
                        file_id, seq_id, chunks[seq_id], 
                        is_last, compress_mode, is_fec_available()
                    )

                    # Enviar frame (hardware maneja reintentos automáticamente)
                    if radio.write(frame):
                        burst_stats['sent'] += 1
                        sent_count += 1
                        success_count += 1
                        pending.discard(seq_id)
                        
                        # Leer ACK inmediatamente (necesario para confirmar recepción)
                        if radio.available():
                            try:
                                size = radio.get_dynamic_payload_size()
                                if 0 < size <= 32:
                                    ack_payload = radio.read(size)
                                    burst_stats['ack'] += 1
                                    
                                    # Procesar ACK
                                    _, missing_seq, is_complete, _ = parse_ack(ack_payload)
                                    if is_complete:
                                        pending.clear()
                                        break
                            except Exception:
                                pass

                        # Mostrar progreso
                        if sent_count % 25 == 0 or is_last:
                            progress = (sent_count / total_packets) * 100
                            elapsed = time.time() - start_time
                            throughput_kibs = (sent_count * chunk_size) / max(elapsed, 1e-9) / 1024
                            print(f"  📊 {progress:.1f}% | {sent_count}/{total_packets} | "
                                  f"{throughput_kibs:.1f} KiB/s")
                    else:
                        burst_stats['fail'] += 1

                if not pending:
                    break

            # Ping final para verificar estado
            if pending:
                time.sleep(0.3)
                last_seq = total_packets - 1
                frame = build_frame(
                    file_id, last_seq, chunks[last_seq], 
                    True, compress_mode, is_fec_available()
                )
                if radio.write(frame) and radio.available():
                    try:
                        size = radio.get_dynamic_payload_size()
                        if 0 < size <= 32:
                            ack_payload = radio.read(size)
                            _, missing_seq, is_complete, _ = parse_ack(ack_payload)
                            if is_complete:
                                print("✓ Receptor confirma recepción completa!")
                                pending.clear()
                                break
                            elif missing_seq is not None:
                                pending = set([s for s in pending if s >= missing_seq])
                    except Exception:
                        pass

        total_time = time.time() - start_time

        # Mostrar resultados
        if not pending:
            throughput_orig = (original_size / max(total_time, 1e-9)) / 1024
            efficiency = (success_count / sent_count * 100) if sent_count > 0 else 0
            compression_ratio = final_size / original_size if original_size > 0 else 1.0
            
            print(f"\n{'='*50}")
            print("✓ ¡TRANSMISIÓN EXITOSA!")
            print(f"{'='*50}")
            print(f"Tiempo total: {total_time:.2f}s")
            print(f"Throughput: {throughput_orig:.2f} KiB/s")
            print(f"Paquetes enviados: {sent_count} (únicos: {success_count})")
            print(f"Eficiencia: {efficiency:.1f}%")
            print(f"Ratio compresión: {compression_ratio:.2%}")
            print(f"Bytes ahorrados: {original_size - final_size}")
            print("Estadísticas burst:")
            print(f"  - Enviados: {burst_stats['sent']}")
            print(f"  - ACKs: {burst_stats['ack']}")
            print(f"  - Fallos: {burst_stats['fail']}")
            if is_fec_available():
                print(f"FEC: Activo (RS corrección)")
            print(f"{'='*50}\n")
            
            led_controller.set_state(SystemState.COMPLETED)
            return True
        else:
            print(f"\n{'='*50}")
            print("✗ TRANSMISIÓN INCOMPLETA")
            print(f"Faltantes: {len(pending)}")
            print(f"Tiempo: {total_time:.2f}s")
            print(f"{'='*50}\n")
            
            led_controller.set_state(SystemState.ERROR)
            return False

    except Exception as e:
        print(f"\n✗ Error en transmisión: {e}")
        import traceback
        traceback.print_exc()
        led_controller.set_state(SystemState.ERROR)
        return False