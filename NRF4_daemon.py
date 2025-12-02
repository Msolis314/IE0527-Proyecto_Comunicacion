#!/usr/bin/env python3
"""
Daemon del sistema de transferencia nRF24L01+
Se ejecuta automáticamente en segundo plano
"""

import sys
import time
import signal
import pathlib
import logging
from logging.handlers import RotatingFileHandler

# Importar módulos del proyecto
from radio_config import initialize_radio
from hardware import LEDController, ButtonController, SystemState, GPIO
from transmitter import transmit_file, transmit_multiple_files
from receiver import receive_file

# Configuración de rutas
BASE_DIR = pathlib.Path(__file__).parent.absolute()
TEXTOS_DIR = BASE_DIR / "Textos"
RECIBIDOS_DIR = BASE_DIR / "recibidos"
DEFAULT_FILE = BASE_DIR / "default.txt"
LOG_FILE = BASE_DIR / "nrf24_daemon.log"

# Configurar logging
def setup_logging():
    """Configura el sistema de logging"""
    logger = logging.getLogger('nrf24_daemon')
    logger.setLevel(logging.INFO)
    
    # Handler rotativo (max 5MB, 3 backups)
    handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=5*1024*1024,
        backupCount=3
    )
    
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # También mostrar en consola si se ejecuta manualmente
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)
    
    return logger

logger = setup_logging()


class NRF24Daemon:
    """Daemon principal del sistema"""
    
    def __init__(self):
        self.running = True
        self.mode = 'idle'
        self.led_controller = None
        self.button_controller = None
        self.radio = None
        
        # Crear directorios necesarios
        self._setup_directories()
        
        # Crear archivo por defecto si no existe
        self._create_default_file()
    
    def _setup_directories(self):
        """Crea los directorios necesarios"""
        try:
            TEXTOS_DIR.mkdir(exist_ok=True)
            RECIBIDOS_DIR.mkdir(exist_ok=True)
            logger.info(f"Directorios configurados: {TEXTOS_DIR}, {RECIBIDOS_DIR}")
        except Exception as e:
            logger.error(f"Error creando directorios: {e}")
    
    def _create_default_file(self):
        """Crea un archivo por defecto para TX simple"""
        if not DEFAULT_FILE.exists():
            try:
                DEFAULT_FILE.write_text(
                    f"Archivo de prueba del sistema nRF24L01+\n"
                    f"Generado: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                )
                logger.info(f"Archivo por defecto creado: {DEFAULT_FILE}")
            except Exception as e:
                logger.error(f"Error creando archivo por defecto: {e}")
    
    def _signal_handler(self, signum, frame):
        """Maneja señales de terminación"""
        logger.info(f"Señal recibida: {signum}, cerrando daemon...")
        self.running = False
    
    def short_press(self):
        """Callback para pulsación corta -> TX"""
        if self.mode == 'idle':
            self.mode = 'tx'
            logger.info("🔘 BOTÓN CORTO → Iniciando TRANSMISIÓN (TX)")
    
    def medium_press(self):
        """Callback para pulsación media -> RX"""
        if self.mode == 'idle':
            self.mode = 'rx'
            logger.info("🔘 BOTÓN MEDIO → Iniciando RECEPCIÓN (RX)")
    
    def long_press(self):
        """Callback para pulsación larga -> TX-MULTI"""
        if self.mode == 'idle':
            self.mode = 'tx-multi'
            logger.info("🔘 BOTÓN LARGO → Iniciando TRANSMISIÓN MÚLTIPLE (TX-MULTI)")
    
    def initialize(self):
        """Inicializa todos los componentes del sistema"""
        try:
            logger.info("="*70)
            logger.info("INICIANDO DAEMON nRF24L01+")
            logger.info("="*70)
            
            # Inicializar radio
            logger.info("Inicializando radio nRF24L01+...")
            self.radio = initialize_radio()
            logger.info("✓ Radio inicializado correctamente")
            
            # Inicializar LEDs
            logger.info("Inicializando LEDs...")
            self.led_controller = LEDController()
            self.led_controller.set_state(SystemState.IDLE)
            logger.info("✓ LEDs inicializados")
            
            # Inicializar botón
            logger.info("Inicializando botón...")
            self.button_controller = ButtonController(
                self.short_press,
                self.medium_press,
                self.long_press
            )
            logger.info("✓ Botón inicializado")
            
            logger.info("✓ Sistema inicializado y listo")
            logger.info("💤 Esperando pulsación de botón...")
            logger.info("="*70)
            
            return True
            
        except Exception as e:
            logger.error(f"✗ Error en inicialización: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def run_tx_mode(self):
        """Ejecuta modo transmisor"""
        try:
            logger.info("\n" + "▶"*35)
            logger.info("MODO TRANSMISOR ACTIVADO")
            logger.info("▶"*35 + "\n")
            
            success = transmit_file(self.radio, DEFAULT_FILE, self.led_controller)
            
            if success:
                logger.info("✓ Transmisión completada exitosamente")
            else:
                logger.warning("✗ Transmisión finalizó con errores")
            
        except Exception as e:
            logger.error(f"✗ Error en modo TX: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.led_controller.set_state(SystemState.ERROR)
        
        finally:
            time.sleep(3)
            self.mode = 'idle'
            self.led_controller.set_state(SystemState.IDLE)
            logger.info("💤 Volviendo a modo Idle\n")
    
    def run_tx_multi_mode(self):
        """Ejecuta modo transmisión múltiple"""
        try:
            logger.info("\n" + "▶"*35)
            logger.info("MODO TRANSMISIÓN MÚLTIPLE ACTIVADO")
            logger.info("▶"*35 + "\n")
            
            stats = transmit_multiple_files(self.radio, TEXTOS_DIR, self.led_controller)
            
            if stats['fallidos'] == 0:
                logger.info(f"✓ Todos los archivos transmitidos ({stats['exitosos']}/{stats['total']})")
            else:
                logger.warning(f"⚠ Transmisión parcial: {stats['exitosos']}/{stats['total']} exitosos")
            
        except Exception as e:
            logger.error(f"✗ Error en modo TX-MULTI: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.led_controller.set_state(SystemState.ERROR)
        
        finally:
            time.sleep(3)
            self.mode = 'idle'
            self.led_controller.set_state(SystemState.IDLE)
            logger.info("💤 Volviendo a modo Idle\n")
    
    def run_rx_mode(self):
        """Ejecuta modo receptor"""
        try:
            logger.info("\n" + "◀"*35)
            logger.info("MODO RECEPTOR ACTIVADO")
            logger.info("◀"*35 + "\n")
            
            success = receive_file(self.radio, RECIBIDOS_DIR, self.led_controller)
            
            if success:
                logger.info("✓ Recepción completada exitosamente")
            else:
                logger.warning("✗ Recepción finalizó con errores")
            
        except Exception as e:
            logger.error(f"✗ Error en modo RX: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.led_controller.set_state(SystemState.ERROR)
        
        finally:
            time.sleep(3)
            self.mode = 'idle'
            self.led_controller.set_state(SystemState.IDLE)
            logger.info("💤 Volviendo a modo Idle\n")
    
    def run(self):
        """Bucle principal del daemon"""
        # Configurar manejadores de señales
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        # Inicializar sistema
        if not self.initialize():
            logger.error("Fallo en la inicialización, terminando daemon")
            return 1
        
        # Bucle principal
        try:
            while self.running:
                if self.mode == 'tx':
                    self.run_tx_mode()
                    
                elif self.mode == 'tx-multi':
                    self.run_tx_multi_mode()
                    
                elif self.mode == 'rx':
                    self.run_rx_mode()
                    
                else:
                    # Modo idle: solo esperar
                    time.sleep(0.1)
                    
        except KeyboardInterrupt:
            logger.info("⏹ Interrupción manual detectada")
        
        except Exception as e:
            logger.error(f"✗ Error en bucle principal: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        finally:
            # Limpieza
            logger.info("\n🧹 Limpiando recursos...")
            if self.led_controller:
                self.led_controller.cleanup()
            if GPIO:
                GPIO.cleanup()
            logger.info("✓ Limpieza completada")
            logger.info("="*70)
            logger.info("DAEMON DETENIDO")
            logger.info("="*70)
        
        return 0


def main():
    """Función principal"""
    daemon = NRF24Daemon()
    return daemon.run()


if __name__ == "__main__":
    sys.exit(main())