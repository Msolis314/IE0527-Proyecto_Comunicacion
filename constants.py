"""
Constantes y configuración del sistema de transferencia nRF24L01+
"""

from pyrf24 import RF24_DRIVER

# ============= GPIO PINES =============
BUTTON_PIN = 17
LED_GREEN = 23
LED_YELLOW = 24
LED_RED = 25

# ============= nRF24L01+ CONFIGURACIÓN =============
CSN_PIN = 0

# Determinar CE_PIN según el driver
if RF24_DRIVER == "MRAA":
    CE_PIN = 15
elif RF24_DRIVER == "wiringPi":
    CE_PIN = 3
else:
    CE_PIN = 22

# Direcciones de comunicación
ADDR_A = b"\xE7\xE7\xE7\xE7\xE7"
ADDR_B = b"\xD7\xD7\xD7\xD7\xD7"

# ============= PARÁMETROS DE TRAMA =============
FRAME_SIZE = 32                # Límite duro de nRF24L01+
HEADER_SIZE = 6                # file_id(2) + seq_id(2) + len(1) + flags(1)

# Sin FEC: 6 + 26 = 32
DATA_BYTES = 26

# Con FEC (RS de 4 símbolos sobre header+data):
FEC_SYMBOLS = 4                # 4 bytes de paridad RS
EFFECTIVE_DATA_BYTES = 22      # 6 + 22 + 4 = 32

# ============= TX OPTIMIZACIÓN =============
MAX_RETRIES = 3
RETRY_DELAY = 0.04
ACK_TIMEOUT = 1.5
MAX_ROUNDS = 20
BURST_SIZE = 15
INTER_PACKET_DELAY = 0  # Optimizado: 0ms (hardware buffers manejan el flujo)

# ============= RX TIEMPOS =============
GLOBAL_TIMEOUT = 120  # 2 minutos para dar tiempo de configurar ambas Pis
IDLE_TIMEOUT = 10     # 10 segundos entre paquetes antes de rendirse

# ============= FLAGS =============
FLAG_LAST = 0x01
FLAG_COMPRESSED = 0x02
FLAG_FEC = 0x08

# ============= COMPRESIÓN =============
COMPRESS_NONE = 0
COMPRESS_ZLIB = 1
COMPRESS_BZ2 = 2
COMPRESS_LZMA = 3

COMPRESS_NAMES = {
    0: "none",
    1: "zlib",
    2: "bz2",
    3: "lzma"
}