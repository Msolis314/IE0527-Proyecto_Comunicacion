"""
Forward Error Correction usando Reed-Solomon
"""

from constants import FEC_SYMBOLS

try:
    from reedsolo import RSCodec
    RS_AVAILABLE = True
    rs_codec = RSCodec(FEC_SYMBOLS)
except ImportError:
    print("⚠ Advertencia: reedsolo no disponible. FEC deshabilitado.")
    print("  Instalar con: pip install reedsolo")
    RS_AVAILABLE = False
    rs_codec = None


def apply_fec(payload_wo_rs: bytes) -> bytes:
    """
    Aplica codificación Reed-Solomon sobre los datos.
    
    Args:
        payload_wo_rs: Datos sin codificar (header + data)
        
    Returns:
        bytes: Datos codificados con FEC (payload + paridad)
    """
    if not RS_AVAILABLE:
        return payload_wo_rs
    
    # RS agrega exactamente FEC_SYMBOLS bytes de paridad
    encoded = rs_codec.encode(payload_wo_rs)
    return encoded


def decode_fec(encoded_payload: bytes) -> tuple[bytes, int]:
    """
    Decodifica Reed-Solomon y corrige errores.
    
    Args:
        encoded_payload: Datos codificados con FEC
        
    Returns:
        tuple: (bytes_corregidos, errores_corregidos)
               Si falla la corrección, errores = -1
    """
    if not RS_AVAILABLE:
        return encoded_payload, 0
    
    try:
        corrected, _, errors = rs_codec.decode(encoded_payload, return_stats=True)
        return bytes(corrected), errors
    except Exception:
        # Fallo en la corrección (demasiados errores)
        return encoded_payload, -1


def is_fec_available() -> bool:
    """Verifica si FEC está disponible"""
    return RS_AVAILABLE