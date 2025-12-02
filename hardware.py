"""
Control de hardware: LEDs y botón
"""

import time
import threading
from enum import Enum
from constants import LED_GREEN, LED_YELLOW, LED_RED, BUTTON_PIN

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    print("⚠ Advertencia: RPi.GPIO no disponible. LEDs y botón deshabilitados.")
    GPIO = None
    GPIO_AVAILABLE = False


class SystemState(Enum):
    """Estados del sistema para indicación visual"""
    IDLE = "idle"
    TX_ACTIVE = "transmitting"
    RX_ACTIVE = "receiving"
    COMPLETED = "completed"
    ERROR = "error"


class LEDController:
    """Controla los 3 LEDs de estado del sistema"""
    
    def __init__(self):
        self.state = SystemState.IDLE
        self.running = True
        self.blink_thread = None
        
        if GPIO_AVAILABLE:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(LED_GREEN, GPIO.OUT)
            GPIO.setup(LED_YELLOW, GPIO.OUT)
            GPIO.setup(LED_RED, GPIO.OUT)
            self.blink_thread = threading.Thread(target=self._blink_loop, daemon=True)
            self.blink_thread.start()

    def _blink_loop(self):
        """Loop de parpadeo para estados IDLE y COMPLETED"""
        while self.running:
            if self.state == SystemState.IDLE:
                GPIO.output(LED_GREEN, GPIO.HIGH)
                time.sleep(0.5)
                GPIO.output(LED_GREEN, GPIO.LOW)
                time.sleep(0.5)
            elif self.state == SystemState.COMPLETED:
                GPIO.output(LED_RED, GPIO.HIGH)
                time.sleep(0.3)
                GPIO.output(LED_RED, GPIO.LOW)
                time.sleep(0.3)
            else:
                time.sleep(0.1)

    def set_state(self, state: SystemState):
        """Cambia el estado visual del sistema"""
        if not GPIO_AVAILABLE:
            self.state = state
            return
            
        self.state = state
        
        # Apagar todos los LEDs primero
        GPIO.output(LED_GREEN, GPIO.LOW)
        GPIO.output(LED_YELLOW, GPIO.LOW)
        GPIO.output(LED_RED, GPIO.LOW)
        
        # Configurar según el estado
        if state in (SystemState.TX_ACTIVE, SystemState.RX_ACTIVE):
            GPIO.output(LED_YELLOW, GPIO.HIGH)
        elif state == SystemState.ERROR:
            GPIO.output(LED_YELLOW, GPIO.HIGH)
            GPIO.output(LED_RED, GPIO.HIGH)

    def cleanup(self):
        """Limpia recursos y apaga LEDs"""
        self.running = False
        if self.blink_thread:
            self.blink_thread.join(timeout=1)
        if GPIO_AVAILABLE:
            GPIO.output(LED_GREEN, GPIO.LOW)
            GPIO.output(LED_YELLOW, GPIO.LOW)
            GPIO.output(LED_RED, GPIO.LOW)


class ButtonController:
    """Controla el botón de cambio de modo con detección de pulsación corta, media y larga"""
    
    def __init__(self, short_press_callback, medium_press_callback, long_press_callback):
        """
        Args:
            short_press_callback: Función a llamar en pulsación corta (< 1s) -> TX
            medium_press_callback: Función a llamar en pulsación media (1-3s) -> RX
            long_press_callback: Función a llamar en pulsación larga (>= 3s) -> TX-MULTI
        """
        self.short_press_callback = short_press_callback
        self.medium_press_callback = medium_press_callback
        self.long_press_callback = long_press_callback
        self.press_start_time = None
        self.medium_press_threshold = 1.0  # 1 segundo
        self.long_press_threshold = 3.0    # 3 segundos
        
        if GPIO_AVAILABLE:
            GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            # Detectar tanto RISING como FALLING para medir duración
            GPIO.add_event_detect(
                BUTTON_PIN,
                GPIO.BOTH,
                callback=self._button_event,
                bouncetime=50
            )

    def _button_event(self, channel):
        """Callback que detecta presión y liberación del botón"""
        if GPIO.input(BUTTON_PIN) == GPIO.HIGH:
            # Botón presionado
            self.press_start_time = time.time()
        else:
            # Botón liberado
            if self.press_start_time is not None:
                press_duration = time.time() - self.press_start_time
                self.press_start_time = None
                
                if press_duration >= self.long_press_threshold:
                    # Pulsación larga -> TX-MULTI
                    if self.long_press_callback:
                        self.long_press_callback()
                elif press_duration >= self.medium_press_threshold:
                    # Pulsación media -> RX
                    if self.medium_press_callback:
                        self.medium_press_callback()
                else:
                    # Pulsación corta -> TX
                    if self.short_press_callback:
                        self.short_press_callback()