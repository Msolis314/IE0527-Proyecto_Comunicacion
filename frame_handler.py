"""
Manejo de tramas: construcción, parseo y ACKs
"""

import hashlib
from constants import (
    FRAME_SIZE, HEADER_SIZE, DATA_BYTES, EFFECTIVE_DATA_BYTES,
    FLAG_LAST, FLAG_COMPRESSED, FLAG_FEC,
    COMPRESS_NONE
)
from fec import apply_fec, decode_fec, is_fec_available


def calculate_file_hash(data: bytes) -> bytes:
    """Calcula hash SHA256 de 4 bytes del archivo"""
    return hashlib.sha256(data).digest()[:4]


def build_frame(file_id: int, seq_id: int, data_bytes: bytes, 
                is_last: bool = False, compress_mode: int = 0, 
                use_fec: bool = True) -> bytes:
    """
    Construye una trama de 32 bytes exactos.
    
    Args:
        file_id: ID del archivo (0-65535)
        seq_id: Número de secuencia del paquete
        data_bytes: Datos a enviar (máx 22 o 26 bytes según FEC)
        is_last: Si es el último paquete
        compress_mode: Modo de compresión usado
        use_fec: Si usar Forward Error Correction
        
    Returns:
        bytes: Trama de 32 bytes lista para transmitir
        
    Raises:
        ValueError: Si los datos exceden el tamaño máximo
    """
    # Determinar tamaño máximo de datos según FEC
    if use_fec and is_fec_available():
        max_data = EFFECTIVE_DATA_BYTES  # 22 bytes
    else:
        max_data = DATA_BYTES            # 26 bytes

    if len(data_bytes) > max_data:
        raise ValueError(f"Data excede {max_data} bytes (len={len(data_bytes)})")

    # Construir flags
    flags = 0
    if is_last:
        flags |= FLAG_LAST
    if compress_mode > 0:
        flags |= FLAG_COMPRESSED
        flags |= (compress_mode << 4)
    if use_fec and is_fec_available():
        flags |= FLAG_FEC

    # Construir header (6 bytes)
    header = (
        int(file_id).to_bytes(2, 'big') +
        int(seq_id).to_bytes(2, 'big') +
        bytes([len(data_bytes)]) +
        bytes([flags])
    )

    # Padding de datos hasta max_data
    data = data_bytes + b"\x00" * (max_data - len(data_bytes))

    # Aplicar FEC si está habilitado
    if use_fec and is_fec_available():
        payload_wo_rs = header + data  # 6 + 22 = 28 bytes
        encoded = apply_fec(payload_wo_rs)  # 28 + 4 = 32 bytes
        if len(encoded) != FRAME_SIZE:
            raise ValueError(f"Payload RS no es 32B (len={len(encoded)})")
        return encoded
    else:
        payload = header + data  # 6 + 26 = 32 bytes
        if len(payload) != FRAME_SIZE:
            raise ValueError(f"Payload sin FEC no es 32B (len={len(payload)})")
        return payload


def parse_frame(pkt: bytes) -> tuple:
    """
    Parsea una trama de 32 bytes, decodifica FEC si está presente.
    
    Args:
        pkt: Paquete recibido de 32 bytes
        
    Returns:
        tuple: (file_id, seq_id, data, is_last, compress_mode, errors_corrected)
               o None si el paquete es inválido
    """
    if len(pkt) != FRAME_SIZE:
        return None

    has_fec = False
    errors_corrected = 0
    raw = pkt

    # Intentar decodificar FEC si está disponible
    if is_fec_available():
        decoded, errors = decode_fec(pkt)
        if errors >= 0 and len(decoded) >= HEADER_SIZE:
            has_fec = True
            errors_corrected = errors
            raw = decoded
        else:
            # Si falla FEC, intentar interpretar raw (modo degradado)
            raw = pkt

    if len(raw) < HEADER_SIZE:
        return None

    # Parsear header
    file_id = int.from_bytes(raw[0:2], 'big')
    seq_id = int.from_bytes(raw[2:4], 'big')
    data_len = raw[4]
    flags = raw[5]

    # Determinar tamaño de datos según flags
    max_data = EFFECTIVE_DATA_BYTES if (flags & FLAG_FEC) else DATA_BYTES
    data_start = HEADER_SIZE
    data_end = data_start + max_data
    data = raw[data_start:data_end]

    if data_len > max_data:
        return None

    # Extraer flags
    is_last = bool(flags & FLAG_LAST)
    is_compressed = bool(flags & FLAG_COMPRESSED)
    compress_mode = ((flags >> 4) & 0x0F) if is_compressed else COMPRESS_NONE

    return file_id, seq_id, data[:data_len], is_last, compress_mode, errors_corrected


def build_ack_payload(file_id: int, chunks: dict, last_seq: int, 
                      last_seen: bool, compress_mode: int = 0) -> bytes:
    """
    Construye un payload de ACK de 6 bytes.
    
    Args:
        file_id: ID del archivo actual (None si no hay archivo)
        chunks: Diccionario de chunks recibidos
        last_seq: Número del último paquete esperado
        last_seen: Si se recibió el paquete marcado como último
        compress_mode: Modo de compresión del archivo
        
    Returns:
        bytes: Payload de ACK (6 bytes)
    """
    if file_id is None:
        # ACK genérico cuando no hay transferencia activa
        return b"\x00\x00\xFF\xFE\x00\x00"
    
    COMPLETE = 1 << 0
    
    if last_seq is None:
        missing_seq = 0xFFFE
        flags = 0
    else:
        # Buscar el primer paquete faltante
        missing = None
        for seq in range(0, last_seq + 1):
            if seq not in chunks:
                missing = seq
                break
        
        if missing is None:
            # No hay faltantes
            missing_seq = 0xFFFF
            flags = COMPLETE if last_seen else 0
        else:
            missing_seq = missing
            flags = 0
    
    return (
        int(file_id).to_bytes(2, 'big') +
        int(missing_seq).to_bytes(2, 'big') +
        bytes([flags]) +
        bytes([compress_mode])
    )


def parse_ack(ack_data: bytes) -> tuple:
    """
    Parsea un payload de ACK.
    
    Args:
        ack_data: Datos del ACK recibido
        
    Returns:
        tuple: (file_id, missing_seq, is_complete, compress_mode)
               missing_seq es None si no hay faltantes o si es 0xFFFF/0xFFFE
    """
    if len(ack_data) < 5:
        return None, None, False, 0
    
    file_id = int.from_bytes(ack_data[0:2], 'big')
    missing_seq = int.from_bytes(ack_data[2:4], 'big')
    flags = ack_data[4]
    compress_mode = ack_data[5] if len(ack_data) > 5 else 0
    
    is_complete = bool(flags & 0x01)
    
    # Valores especiales
    if missing_seq in (0xFFFF, 0xFFFE):
        missing_seq = None
    
    return file_id, missing_seq, is_complete, compress_mode