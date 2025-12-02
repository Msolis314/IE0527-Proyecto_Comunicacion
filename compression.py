"""
Compresión y descompresión adaptativa de datos
"""

import time
import zlib
import bz2
import lzma
from constants import COMPRESS_NONE, COMPRESS_ZLIB, COMPRESS_BZ2, COMPRESS_LZMA


def adaptive_compress(data: bytes) -> tuple[bytes, int, float]:
    """
    Comprime datos usando el algoritmo que mejor ratio logre.
    
    Args:
        data: Datos a comprimir
        
    Returns:
        tuple: (datos_comprimidos, modo_compresion, ratio)
    """
    # Para archivos pequeños, no vale la pena comprimir
    if len(data) < 512:
        return data, COMPRESS_NONE, 1.0
    
    results = []
    
    # Probar zlib (rápido, balanceado)
    try:
        t0 = time.time()
        c = zlib.compress(data, level=6)
        results.append((c, COMPRESS_ZLIB, len(c)/len(data), time.time()-t0, "zlib"))
    except Exception:
        pass
    
    # Probar bz2 (mejor compresión, más lento) - solo para archivos > 5KB
    if len(data) > 5000:
        try:
            t0 = time.time()
            c = bz2.compress(data, compresslevel=5)
            results.append((c, COMPRESS_BZ2, len(c)/len(data), time.time()-t0, "bz2"))
        except Exception:
            pass
    
    # Probar lzma (excelente compresión, muy lento) - solo para archivos > 10KB
    if len(data) > 10000:
        try:
            t0 = time.time()
            c = lzma.compress(data, preset=3)
            results.append((c, COMPRESS_LZMA, len(c)/len(data), time.time()-t0, "lzma"))
        except Exception:
            pass
    
    # Siempre incluir "sin compresión" como opción
    results.append((data, COMPRESS_NONE, 1.0, 0, "none"))
    
    # Elegir el mejor ratio
    best = min(results, key=lambda x: x[2])
    
    # Solo usar compresión si ahorra al menos 10%
    if best[2] < 0.90:
        print(f"  ✓ Compresión: {best[4]} - {len(data)} → {len(best[0])} bytes "
              f"(ratio: {best[2]:.2%}, tiempo: {best[3]:.3f}s)")
        return best[0], best[1], best[2]
    else:
        print(f"  ○ Sin compresión (mejor ratio: {best[2]:.2%} con {best[4]})")
        return data, COMPRESS_NONE, 1.0


def adaptive_decompress(data: bytes, mode: int) -> bytes:
    """
    Descomprime datos según el modo especificado.
    
    Args:
        data: Datos comprimidos
        mode: Modo de compresión (COMPRESS_*)
        
    Returns:
        bytes: Datos descomprimidos
        
    Raises:
        ValueError: Si el modo es desconocido
    """
    if mode == COMPRESS_NONE:
        return data
    elif mode == COMPRESS_ZLIB:
        return zlib.decompress(data)
    elif mode == COMPRESS_BZ2:
        return bz2.decompress(data)
    elif mode == COMPRESS_LZMA:
        return lzma.decompress(data)
    else:
        raise ValueError(f"Modo de compresión desconocido: {mode}")