"""
Lógica de recepción de archivos
"""

import time
import pathlib
from pyrf24 import RF24
from constants import (
    ADDR_A, ADDR_B, FRAME_SIZE, GLOBAL_TIMEOUT, IDLE_TIMEOUT,
    COMPRESS_NONE, COMPRESS_NAMES
)
from compression import adaptive_decompress
from frame_handler import parse_frame, build_ack_payload
from fec import is_fec_available
from hardware import LEDController, SystemState


def receive_file(radio: RF24, dest_dir: pathlib.Path, 
                 led_controller: LEDController) -> bool:
    """
    Recibe un archivo completo usando nRF24L01+.
    
    Args:
        radio: Objeto RF24 inicializado
        dest_dir: Directorio donde guardar el archivo recibido
        led_controller: Controlador de LEDs
        
    Returns:
        bool: True si la recepción fue exitosa, False en caso contrario
    """
    print("\n[ MODO RECEPTOR ]")
    led_controller.set_state(SystemState.RX_ACTIVE)
    
    try:
        # Configurar pipes
        radio.open_rx_pipe(1, ADDR_A)
        radio.open_tx_pipe(ADDR_B)
        radio.start_listening()

        print(f"\n{'='*50}")
        print("MODO RECEPTOR (OPTIMIZADO)")
        print(f"{'='*50}")
        print(f"Directorio: {dest_dir.absolute()}")
        print(f"FEC: {'Habilitado' if is_fec_available() else 'Deshabilitado'}")
        print("Esperando datos...\n")

        # Estado de recepción
        file_id_seen = None
        chunks = {}
        last_seq = None
        last_seen = False
        compress_mode = COMPRESS_NONE
        start_time = None  # Iniciar cronómetro al recibir primer paquete
        last_packet_time = None
        packets_received = 0
        total_errors_corrected = 0

        # Enviar ACK inicial
        first_ack = build_ack_payload(file_id_seen, chunks, last_seq, last_seen)
        radio.write_ack_payload(1, first_ack)

        # Bucle principal de recepción
        while True:
            now = time.monotonic()
            
            # Verificar timeouts (solo si ya empezó la transferencia)
            if start_time is not None:
                if (now - start_time) > GLOBAL_TIMEOUT:
                    print("⏱ Timeout global alcanzado")
                    break
            
            if last_seen and last_packet_time is not None:
                if (now - last_packet_time) > IDLE_TIMEOUT:
                    print("⏱ Timeout de inactividad")
                    break

            # Verificar si hay datos disponibles
            has_payload, pipe = radio.available_pipe()
            if not has_payload:
                time.sleep(0.001)
                continue

            # Leer payload
            try:
                payload_size = radio.get_dynamic_payload_size()
            except Exception:
                payload_size = 0

            if payload_size == 0 or payload_size > FRAME_SIZE:
                try:
                    radio.read(payload_size if payload_size > 0 else 32)
                except Exception:
                    pass
                ack_payload = build_ack_payload(
                    file_id_seen, chunks, last_seq, last_seen, compress_mode
                )
                radio.write_ack_payload(1, ack_payload)
                continue

            # Leer y ajustar tamaño si es necesario
            raw = radio.read(payload_size)
            if len(raw) < FRAME_SIZE:
                raw += b"\x00" * (FRAME_SIZE - len(raw))

            # Parsear frame
            parsed = parse_frame(raw)
            if parsed is None:
                ack_payload = build_ack_payload(
                    file_id_seen, chunks, last_seq, last_seen, compress_mode
                )
                radio.write_ack_payload(1, ack_payload)
                continue

            fid, seq_id, data_bytes, is_last, pkt_compress, errors = parsed
            last_packet_time = now
            packets_received += 1
            
            # Iniciar cronómetro al recibir primer paquete
            if start_time is None:
                start_time = now
            
            if errors > 0:
                total_errors_corrected += errors

            # Primer paquete: establecer contexto
            if file_id_seen is None:
                file_id_seen = fid
                compress_mode = pkt_compress
                print(f"→ File ID: {file_id_seen} | "
                      f"Compresión: {COMPRESS_NAMES.get(compress_mode, 'unknown')}\n")

            # Verificar que sea del archivo actual
            if fid != file_id_seen:
                ack_payload = build_ack_payload(
                    file_id_seen, chunks, last_seq, last_seen, compress_mode
                )
                radio.write_ack_payload(1, ack_payload)
                continue

            # Almacenar chunk si es nuevo
            if seq_id not in chunks:
                chunks[seq_id] = data_bytes
                
                # Mostrar progreso
                if packets_received % 25 == 0 or is_last:
                    progress = len(chunks)
                    elapsed = time.monotonic() - start_time
                    per_pkt = len(data_bytes)
                    throughput = (progress * per_pkt) / max(elapsed, 1e-9) / 1024
                    print(f"  📊 {progress} paquetes | {throughput:.1f} KiB/s | "
                          f"Errores FEC: {total_errors_corrected}")

            # Marcar si es el último paquete
            if is_last:
                last_seq = seq_id
                last_seen = True
                print(f"\n→ Último paquete recibido: {last_seq}")
                print(f"  Total recibidos: {len(chunks)} de {last_seq + 1}")
            
            # Verificar si ya tenemos todos los paquetes (salir inmediatamente)
            if last_seen and last_seq is not None:
                if len(chunks) == last_seq + 1:
                    print("✓ Transferencia completa, finalizando...")
                    break

            # Enviar ACK
            ack_payload = build_ack_payload(
                file_id_seen, chunks, last_seq, last_seen, compress_mode
            )
            radio.write_ack_payload(1, ack_payload)

        radio.stop_listening()
        total_time = time.monotonic() - start_time

        # Verificar si se recibieron datos
        if not chunks:
            print("\n✗ No se recibieron datos")
            led_controller.set_state(SystemState.ERROR)
            return False

        print(f"\n{'='*50}")
        print("RECONSTRUYENDO ARCHIVO")
        print(f"{'='*50}")

        # Reconstruir archivo
        max_seq = max(chunks.keys())
        reconstructed = bytearray()
        missing = []
        
        for s in range(0, max_seq + 1):
            if s in chunks:
                reconstructed += chunks[s]
            else:
                missing.append(s)

        if missing:
            print(f"⚠ Paquetes faltantes: {len(missing)}")
            head = ','.join(map(str, missing[:20]))
            print(f"  Lista: {head}{'...' if len(missing) > 20 else ''}")

        # Descomprimir si es necesario
        original_size = len(reconstructed)
        if compress_mode != COMPRESS_NONE:
            print("Descomprimiendo datos...")
            try:
                decompressed = adaptive_decompress(bytes(reconstructed), compress_mode)
                reconstructed = bytearray(decompressed)
                print(f"  {original_size} → {len(reconstructed)} bytes")
            except Exception as e:
                print(f"✗ Error al descomprimir: {e}")
                led_controller.set_state(SystemState.ERROR)
                return False

        # Guardar archivo
        timestamp = int(time.time())
        filename = f"file_{file_id_seen}_{timestamp}.bin" if file_id_seen else f"file_{timestamp}.bin"
        dest_path = dest_dir / filename
        dest_path.write_bytes(reconstructed)

        # Mostrar resultados
        throughput = (len(reconstructed) / max(total_time, 1e-9)) / 1024
        
        print(f"✓ Archivo guardado: {dest_path.name}")
        print(f"  Tamaño final: {len(reconstructed)} bytes")
        print(f"  Paquetes: {len(chunks)}/{max_seq + 1}")
        print(f"  Tiempo: {total_time:.2f}s")
        print(f"  Throughput: {throughput:.2f} KiB/s")
        
        if total_errors_corrected > 0:
            print(f"  Errores corregidos (FEC): {total_errors_corrected}")
        
        print(f"  Faltantes: {len(missing)}")

        if missing:
            print(f"{'='*50}\n")
            led_controller.set_state(SystemState.ERROR)
            return False
        else:
            print("✓ ¡Recepción completa sin pérdidas!")
            print(f"{'='*50}\n")
            led_controller.set_state(SystemState.COMPLETED)
            return True

    except Exception as e:
        print(f"\n✗ Error en recepción: {e}")
        import traceback
        traceback.print_exc()
        led_controller.set_state(SystemState.ERROR)
        radio.stop_listening()
        return False