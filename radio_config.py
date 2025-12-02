"""
Configuración del módulo nRF24L01+
"""

from pyrf24 import RF24, RF24_PA_MAX, RF24_2MBPS
from constants import CE_PIN, CSN_PIN


def initialize_radio() -> RF24:
    """
    Inicializa y configura el módulo nRF24L01+.
    
    Returns:
        RF24: Objeto radio configurado y listo para usar
        
    Raises:
        RuntimeError: Si falla la inicialización del radio
    """
    radio = RF24(CE_PIN, CSN_PIN)
    
    if not radio.begin():
        raise RuntimeError("✗ Error al inicializar nRF24L01+. Verifica las conexiones.")
    
    # Configuración óptima para máxima velocidad
    radio.set_pa_level(RF24_PA_MAX)      # Máxima potencia
    radio.dynamic_payloads = True         # Payloads dinámicos
    radio.ack_payloads = True             # ACK con payload
    radio.channel = 90                    # Canal RF (evita WiFi)
    radio.data_rate = RF24_2MBPS          # 2 Mbps
    radio.set_retries(5, 15)              # (delay, count)
    
    print("✓ Radio nRF24L01+ inicializado correctamente")
    print(f"  CE Pin: {CE_PIN}")
    print(f"  CSN Pin: {CSN_PIN}")
    print(f"  Canal: {radio.channel}")
    print(f"  Data Rate: 2 MBPS")
    print(f"  PA Level: MAX")
    
    return radio