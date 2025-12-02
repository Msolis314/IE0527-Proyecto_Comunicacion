# Sistema de Transmisión de Archivos nRF24L01+ con Daemon Autónomo

## Resumen

Este proyecto implementa un sistema de transmisión de archivos bidireccional utilizando módulos de radio nRF24L01+ en Raspberry Pi. El sistema opera como un daemon (servicio del sistema) completamente autónomo, ejecutándose en segundo plano sin intervención del usuario. La arquitectura permite tres modos de operación controlados mediante un botón físico: transmisión de archivo único, recepción de archivos, y transmisión múltiple de archivos.

El sistema ha sido optimizado para alcanzar un throughput de aproximadamente 32 KiB/s, incorpora compresión adaptativa de datos, corrección de errores mediante Reed-Solomon, y proporciona monitoreo completo a través de logs persistentes.

---

## Tabla de Contenidos

1. [Características Principales](#características-principales)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Requisitos del Sistema](#requisitos-del-sistema)
4. [Instalación](#instalación)
5. [Configuración de Hardware](#configuración-de-hardware)
6. [Uso del Sistema](#uso-del-sistema)
7. [Gestión del Daemon](#gestión-del-daemon)
8. [Estructura de Archivos](#estructura-de-archivos)
9. [Protocolo de Comunicación](#protocolo-de-comunicación)
10. [Optimizaciones Implementadas](#optimizaciones-implementadas)
11. [Sistema de Logs](#sistema-de-logs)
12. [Solución de Problemas](#solución-de-problemas)
13. [Especificaciones Técnicas](#especificaciones-técnicas)
14. [Referencias](#referencias)

---

## Características Principales

### Daemon Autónomo
- Inicio automático con el sistema operativo mediante systemd
- Ejecución continua en segundo plano
- Auto-recuperación ante fallos con reinicio inteligente
- Gestión de recursos con límites configurados (256 MB RAM, 50% CPU)

### Modos de Operación
- **TX (Transmisión)**: Envío de un archivo individual
- **RX (Recepción)**: Recepción de archivos entrantes
- **TX-MULTI (Transmisión Múltiple)**: Envío automático de todos los archivos .txt en un directorio

### Optimizaciones de Transmisión
- Throughput de aproximadamente 32 KiB/s
- Compresión adaptativa (zlib, bz2, lzma) seleccionada automáticamente
- Forward Error Correction mediante códigos Reed-Solomon (4 símbolos de paridad)
- Eficiencia de transmisión del 99-100%
- Tasa de datos de 2 Mbps en la capa física

### Interfaz de Usuario
- Control mediante botón físico con tres tipos de pulsación
- Indicadores visuales mediante LEDs
- Logs rotativos persistentes para auditoría
- Scripts de gestión simplificada

---

## Arquitectura del Sistema

### Diagrama de Capas

```
+------------------------------------------------------------------+
|                      Sistema Operativo                           |
|                    (Raspberry Pi OS / Linux)                     |
+------------------------------------------------------------------+
                              |
                              v
+------------------------------------------------------------------+
|                         systemd                                  |
|               (Gestor de servicios del sistema)                  |
+------------------------------------------------------------------+
                              |
                              v
+------------------------------------------------------------------+
|                   nrf24-daemon.service                           |
|            (Definición del servicio systemd)                     |
+------------------------------------------------------------------+
                              |
                              v
+------------------------------------------------------------------+
|                     nrf24_daemon.py                              |
|                   (Daemon principal)                             |
|                                                                  |
|  +-----------------------------------------------------------+  |
|  |  Inicialización:                                          |  |
|  |  - Radio nRF24L01+ (SPI)                                 |  |
|  |  - LEDs indicadores (GPIO 23, 24, 25)                   |  |
|  |  - Botón de control (GPIO 17)                           |  |
|  +-----------------------------------------------------------+  |
|                                                                  |
|  +-----------------------------------------------------------+  |
|  |  Bucle Principal:                                         |  |
|  |  1. Estado IDLE (esperando evento)                       |  |
|  |  2. Detección de pulsación de botón                      |  |
|  |  3. Ejecución del modo correspondiente                   |  |
|  |  4. Registro de actividad en logs                        |  |
|  |  5. Retorno a IDLE                                       |  |
|  +-----------------------------------------------------------+  |
+------------------------------------------------------------------+
        |               |                |
        v               v                v
+---------------+ +-------------+ +------------------+
| transmitter.py| | receiver.py | |  hardware.py     |
| - TX          | | - RX        | |  - LEDs          |
| - TX-MULTI    | | - ACKs      | |  - Botón         |
+---------------+ +-------------+ +------------------+
        |               |
        v               v
+----------------------------------+
|      frame_handler.py            |
|  - Construcción de tramas        |
|  - Parseo de tramas              |
|  - Manejo de ACKs                |
+----------------------------------+
        |               |
        v               v
+---------------+ +-------------+
| compression.py| |   fec.py    |
| - Compresión  | | - Reed-     |
| - Descompresi.| |   Solomon   |
+---------------+ +-------------+
```

### Flujo de Estados del Daemon

```
  [Inicio del Sistema]
          |
          v
  [Inicialización]
    - Radio
    - LEDs
    - Botón
          |
          v
    [Estado IDLE]
    LED Verde Parpadeando
          |
          +------------------+-------------------+
          |                  |                   |
    (< 1 seg)          (1-3 seg)            (>= 3 seg)
          |                  |                   |
          v                  v                   v
      [Modo TX]          [Modo RX]         [Modo TX-MULTI]
    LED Amarillo       LED Amarillo        LED Amarillo
          |                  |                   |
          v                  v                   v
   [Transmisión]       [Recepción]      [Transmisión Múltiple]
          |                  |                   |
          v                  v                   v
   [Completado]        [Completado]         [Completado]
   LED Rojo            LED Rojo             LED Rojo
   Parpadeando         Parpadeando          Parpadeando
          |                  |                   |
          +------------------+-------------------+
                            |
                            v
                      [Retorno a IDLE]
                     (Espera 3 segundos)
```

---

## Requisitos del Sistema

### Hardware
- 2x Raspberry Pi (cualquier modelo con GPIO y SPI)
- 2x Módulos nRF24L01+ (con capacitor de desacoplamiento recomendado)
- 1x Botón pulsador (normalmente abierto)
- 3x LEDs (verde, amarillo, rojo)
- 3x Resistencias 220-330 Ohm para LEDs
- Cables de conexión y breadboard

### Software
- Sistema Operativo: Raspberry Pi OS (Raspbian) o compatible
- Python 3.7 o superior
- Bibliotecas Python:
  - pyrf24 (interfaz con nRF24L01+)
  - reedsolo (corrección de errores Reed-Solomon)
  - RPi.GPIO (control de GPIO)
- SPI habilitado en el sistema

### Configuración del Sistema
- Usuario con permisos para grupos: spi, gpio
- systemd para gestión de servicios
- Aproximadamente 100 MB de espacio en disco

---

## Instalación

### Instalación Automatizada (Recomendada)

El sistema incluye un script de instalación que configura todo automáticamente:

```bash
# 1. Copiar todos los archivos al directorio del proyecto
mkdir ~/nrf24-transmision
cd ~/nrf24-transmision
# Copiar archivos aquí

# 2. Hacer ejecutable el instalador
chmod +x install_daemon.sh

# 3. Ejecutar con privilegios de superusuario
sudo ./install_daemon.sh
```

El instalador realiza las siguientes operaciones:
1. Verifica requisitos del sistema
2. Habilita la interfaz SPI si es necesario
3. Crea la estructura de directorios
4. Instala dependencias Python
5. Configura permisos de usuario
6. Instala el servicio systemd
7. Habilita inicio automático
8. Genera archivos de prueba

### Instalación Manual

Para instalación manual, seguir los pasos documentados en `INSTALACION.md`.

### Verificación de la Instalación

```bash
# Verificar estado del servicio
sudo systemctl status nrf24-daemon

# Verificar SPI
ls -l /dev/spidev0.0

# Verificar permisos
groups pi | grep -E "spi|gpio"

# Verificar logs
tail -n 20 ~/nrf24-transmision/nrf24_daemon.log
```

---

## Configuración de Hardware

### Conexiones del Módulo nRF24L01+

| Pin nRF24L01+ | GPIO Raspberry Pi | Pin Físico | Descripción |
|---------------|-------------------|------------|-------------|
| VCC | 3.3V | 1 | Alimentación (IMPORTANTE: 3.3V, NO 5V) |
| GND | GND | 6 | Tierra |
| CE | GPIO 22 | 15 | Chip Enable |
| CSN | GPIO 0 (SPI CS0) | 24 | Chip Select |
| SCK | GPIO 11 (SPI SCLK) | 23 | SPI Clock |
| MOSI | GPIO 10 (SPI MOSI) | 19 | SPI Master Out |
| MISO | GPIO 9 (SPI MISO) | 21 | SPI Master In |
| IRQ | No conectado | - | No utilizado |

### Conexiones de LEDs

| LED | GPIO | Pin Físico | Resistencia |
|-----|------|------------|-------------|
| Verde | GPIO 23 | 16 | 220-330 Ohm |
| Amarillo | GPIO 24 | 18 | 220-330 Ohm |
| Rojo | GPIO 25 | 22 | 220-330 Ohm |

Esquema: GPIO -> Resistencia -> LED (ánodo) -> LED (cátodo) -> GND

### Conexión del Botón

| Terminal | Conexión | Pin Físico |
|----------|----------|------------|
| Terminal 1 | GPIO 17 | 11 |
| Terminal 2 | 3.3V | 1 |

Configuración interna: Pull-down habilitado en software

### Diagrama de Conexión

```
Raspberry Pi                    nRF24L01+
    [3.3V] Pin 1  ------------- VCC
    [GND]  Pin 6  ------------- GND
    [GP22] Pin 15 ------------- CE
    [GP0]  Pin 24 ------------- CSN
    [GP11] Pin 23 ------------- SCK
    [GP10] Pin 19 ------------- MOSI
    [GP9]  Pin 21 ------------- MISO

LEDs:
    [GP23] Pin 16 --[220Ω]--LED_VERDE--[GND]
    [GP24] Pin 18 --[220Ω]--LED_AMARILLO--[GND]
    [GP25] Pin 22 --[220Ω]--LED_ROJO--[GND]

Botón:
    [3.3V] Pin 1  --BOTON-- [GP17] Pin 11
                              (Pull-down interno)
```

---

## Uso del Sistema

### Inicio del Sistema

El daemon se inicia automáticamente al encender la Raspberry Pi. No se requiere intervención manual. El LED verde parpadeará indicando que el sistema está en modo IDLE esperando comandos.

### Control mediante Botón

El sistema utiliza un único botón con detección de duración de pulsación:

| Duración de Pulsación | Modo Activado | Descripción |
|----------------------|---------------|-------------|
| Menor a 1 segundo | TX | Transmite el archivo por defecto (default.txt) |
| Entre 1 y 3 segundos | RX | Activa modo receptor para recibir archivos |
| Mayor o igual a 3 segundos | TX-MULTI | Transmite todos los archivos .txt del directorio Textos/ |

### Modo TX (Transmisión de Archivo Único)

1. Sistema en estado IDLE (LED verde parpadeando)
2. Usuario presiona el botón brevemente (< 1 segundo)
3. LED cambia a amarillo fijo
4. Sistema transmite el archivo default.txt
5. Al completar, LED rojo parpadea por 3 segundos
6. Sistema retorna a IDLE

### Modo RX (Recepción)

1. Sistema en estado IDLE (LED verde parpadeando)
2. Usuario presiona el botón por 1-3 segundos
3. LED cambia a amarillo fijo
4. Sistema espera recibir archivos (timeout: 120 segundos global, 10 segundos entre paquetes)
5. Archivos recibidos se guardan en el directorio recibidos/
6. Al completar, LED rojo parpadea por 3 segundos
7. Sistema retorna a IDLE

### Modo TX-MULTI (Transmisión Múltiple)

1. Colocar archivos .txt en el directorio ~/nrf24-transmision/Textos/
2. Sistema en estado IDLE (LED verde parpadeando)
3. Usuario presiona el botón por 3 o más segundos
4. LED cambia a amarillo fijo
5. Sistema transmite todos los archivos .txt en orden alfabético
6. Pausa de 2 segundos entre cada archivo
7. Al completar todos, LED rojo parpadea por 3 segundos
8. Sistema retorna a IDLE

### Generación de Archivos de Prueba

```bash
cd ~/nrf24-transmision

# Generar 5 archivos de prueba
python3 generar_archivos_prueba.py

# Generar cantidad específica
python3 generar_archivos_prueba.py --num 10

# Listar archivos disponibles
python3 generar_archivos_prueba.py --list

# Limpiar archivos de prueba
python3 generar_archivos_prueba.py --clean
```

---

## Gestión del Daemon

### Script de Control Simplificado

El sistema incluye un script de gestión que simplifica las operaciones comunes:

```bash
# Ver estado del daemon
./daemon_control.sh status

# Iniciar el daemon
./daemon_control.sh start

# Detener el daemon
./daemon_control.sh stop

# Reiniciar el daemon
./daemon_control.sh restart

# Ver logs en tiempo real
./daemon_control.sh logs

# Ver histórico de logs (últimas 50 líneas)
./daemon_control.sh history

# Habilitar inicio automático
./daemon_control.sh enable

# Deshabilitar inicio automático
./daemon_control.sh disable

# Ver ayuda
./daemon_control.sh help
```

### Comandos systemd Nativos

Para control más detallado, utilizar los comandos de systemd:

```bash
# Ver estado detallado
sudo systemctl status nrf24-daemon

# Iniciar servicio
sudo systemctl start nrf24-daemon

# Detener servicio
sudo systemctl stop nrf24-daemon

# Reiniciar servicio
sudo systemctl restart nrf24-daemon

# Habilitar inicio automático
sudo systemctl enable nrf24-daemon

# Deshabilitar inicio automático
sudo systemctl disable nrf24-daemon

# Ver logs del sistema
sudo journalctl -u nrf24-daemon -f

# Ver logs desde un tiempo específico
sudo journalctl -u nrf24-daemon --since "2 hours ago"

# Ver solo errores
sudo journalctl -u nrf24-daemon -p err
```

---

## Estructura de Archivos

### Distribución en el Sistema

```
/home/pi/nrf24-transmision/
│
├── Código Principal
│   ├── nrf24_daemon.py           # Daemon principal del sistema
│   ├── main.py                   # Punto de entrada alternativo (modo terminal)
│   ├── transmitter.py            # Lógica de transmisión
│   ├── receiver.py               # Lógica de recepción
│   ├── hardware.py               # Control de LEDs y botón
│   └── radio_config.py           # Configuración del radio
│
├── Protocolo y Codificación
│   ├── frame_handler.py          # Construcción y parseo de tramas
│   ├── compression.py            # Compresión adaptativa
│   ├── fec.py                    # Forward Error Correction
│   └── constants.py              # Constantes del sistema
│
├── Utilidades
│   ├── generar_archivos_prueba.py  # Generador de archivos de testing
│   ├── daemon_control.sh         # Script de gestión del daemon
│   ├── install_daemon.sh         # Instalador automático
│   └── uninstall_daemon.sh       # Desinstalador
│
├── Datos
│   ├── Textos/                   # Archivos a transmitir (TX-MULTI)
│   │   ├── archivo_01.txt
│   │   └── ...
│   ├── recibidos/                # Archivos recibidos
│   │   └── ...
│   └── default.txt               # Archivo por defecto (TX)
│
├── Logs
│   ├── nrf24_daemon.log          # Log principal (rotativo)
│   ├── nrf24_daemon.log.1        # Backup 1
│   └── nrf24_daemon.log.2        # Backup 2
│
└── Configuración
    └── nrf24-daemon.service      # Archivo de servicio systemd
                                  # (instalado en /etc/systemd/system/)
```

### Descripción de Módulos

**nrf24_daemon.py**
- Daemon principal que se ejecuta como servicio del sistema
- Gestiona el bucle principal de estados
- Inicializa todos los componentes
- Maneja señales del sistema (SIGTERM, SIGINT)
- Registra toda la actividad en logs

**transmitter.py**
- Implementa la lógica de transmisión de archivos
- Funciones: `transmit_file()` y `transmit_multiple_files()`
- Maneja división de archivos en chunks
- Implementa sistema de reintentos selectivos
- Procesa ACKs del receptor

**receiver.py**
- Implementa la lógica de recepción de archivos
- Reconstruye archivos a partir de chunks
- Envía ACKs con información de chunks faltantes
- Maneja timeouts de inactividad

**frame_handler.py**
- Construye tramas de 32 bytes para transmisión
- Parsea tramas recibidas
- Construye y parsea payloads de ACK
- Integra FEC en las tramas cuando está disponible

**compression.py**
- Implementa compresión adaptativa
- Selecciona automáticamente el mejor algoritmo (zlib, bz2, lzma)
- Función `adaptive_compress()` retorna datos comprimidos y ratio
- Función `adaptive_decompress()` descomprime según modo

**fec.py**
- Implementa Forward Error Correction usando Reed-Solomon
- 4 símbolos de paridad por trama
- Capacidad de corrección: hasta 2 errores por trama
- Funciones: `apply_fec()` y `decode_fec()`

**hardware.py**
- Controla LEDs indicadores (GPIO 23, 24, 25)
- Gestiona entrada del botón (GPIO 17)
- Implementa detección de duración de pulsación
- Define clase `LEDController` y `ButtonController`

---

## Protocolo de Comunicación

### Estructura de Trama

El sistema utiliza tramas de tamaño fijo de 32 bytes, que es el límite máximo del hardware nRF24L01+.

#### Trama sin FEC (26 bytes de datos útiles)

```
+----------+----------+----------+----------+-------+--------+------------------+
| file_id  | seq_id   | data_len | flags    | data  (26 bytes)                  |
| 2 bytes  | 2 bytes  | 1 byte   | 1 byte   |                                  |
+----------+----------+----------+----------+-------+--------+------------------+
|<------- 6 bytes header ------->|<------- 26 bytes payload ------------------>|
|<-------------------------- 32 bytes total ---------------------------------->|
```

#### Trama con FEC (22 bytes de datos útiles + 4 bytes de paridad)

```
+----------+----------+----------+----------+-------+--------+------------+
| file_id  | seq_id   | data_len | flags    | data  (22 bytes) | RS Parity|
| 2 bytes  | 2 bytes  | 1 byte   | 1 byte   |                  | 4 bytes  |
+----------+----------+----------+----------+-------+--------+-------------+
|<------- 6 bytes header ------->|<-- 22 -->|<-- 4 -->|
|<-------------- 28 bytes sin paridad ------>|
|<-------------------------- 32 bytes total -------------------------------->|
```

### Campos de la Trama

**file_id (2 bytes)**
- Identificador único del archivo en transmisión
- Rango: 0 - 65535
- Generado aleatoriamente al inicio de cada transmisión

**seq_id (2 bytes)**
- Número de secuencia del paquete
- Rango: 0 - 65535
- Secuencial, comenzando en 0 para cada archivo

**data_len (1 byte)**
- Longitud real de los datos en este paquete
- Rango: 0 - 26 (sin FEC) o 0 - 22 (con FEC)
- El resto del campo de datos es padding (relleno con ceros)

**flags (1 byte)**
- Bit 0 (FLAG_LAST): Indica si es el último paquete del archivo
- Bit 1 (FLAG_COMPRESSED): Indica si el archivo está comprimido
- Bit 3 (FLAG_FEC): Indica si la trama incluye FEC
- Bits 4-7: Modo de compresión (0=none, 1=zlib, 2=bz2, 3=lzma)

**data (22 o 26 bytes)**
- Datos del archivo
- Padding con ceros hasta completar el tamaño

**RS Parity (4 bytes, solo con FEC)**
- Símbolos de paridad Reed-Solomon
- Calculados sobre header + data (28 bytes)
- Permiten corregir hasta 2 errores por trama

### Estructura de ACK

Los ACKs son payloads de 6 bytes enviados automáticamente por el receptor:

```
+----------+-------------+-------+---------------+
| file_id  | missing_seq | flags | compress_mode |
| 2 bytes  | 2 bytes     | 1 byte| 1 byte        |
+----------+-------------+-------+---------------+
```

**missing_seq**
- Primer número de secuencia faltante
- 0xFFFF: No hay faltantes
- 0xFFFE: ACK genérico (sin transferencia activa)

**flags**
- Bit 0 (COMPLETE): Indica transferencia completa

### Flujo de Transmisión

```
Transmisor                                    Receptor
    |                                              |
    |------ Paquete 0 (file_id=1234, seq=0) ----->|
    |<----- ACK (missing=1) -----------------------|
    |                                              |
    |------ Paquete 1 (seq=1) -------------------->|
    |<----- ACK (missing=2) -----------------------|
    |                                              |
    |------ Paquete 2 (seq=2) -------------------->|
    |<----- ACK (missing=3) -----------------------|
    |                                              |
    |   ... (continúa hasta último paquete)        |
    |                                              |
    |------ Paquete N (seq=N, FLAG_LAST) -------->|
    |<----- ACK (missing=0xFFFF, COMPLETE) --------|
    |                                              |
```

### Sistema de Reintentos

El sistema utiliza reintentos selectivos basados en ACKs:

1. **Transmisión en ráfagas**: Envía hasta 15 paquetes consecutivos
2. **Lectura de ACKs**: Lee ACK después de cada paquete
3. **Identificación de faltantes**: ACK indica primer paquete faltante
4. **Retransmisión selectiva**: Solo reenvía paquetes no confirmados
5. **Límite de rondas**: Máximo 20 rondas de retransmisión

El hardware nRF24L01+ también proporciona auto-retransmit a nivel físico:
- 15 intentos automáticos por paquete
- Delay de 5 × 250μs = 1.25ms entre reintentos

---

## Optimizaciones Implementadas

### Optimización 1: Eliminación de Delays Artificiales

**Implementación**: INTER_PACKET_DELAY = 0

**Justificación**: El hardware nRF24L01+ cuenta con buffers de 3 niveles que gestionan el flujo de datos automáticamente. Los delays artificiales entre paquetes reducían el throughput sin proporcionar beneficios.

**Resultado**: Incremento del 110% en velocidad (de ~15 KiB/s a ~32 KiB/s)

### Optimización 2: Auto-Retransmit en Hardware

**Implementación**: `radio.set_retries(5, 15)`

**Justificación**: Utilizar los reintentos automáticos del hardware es más eficiente que implementar reintentos en software. El hardware gestiona reintentos a nivel de microsegundos.

**Parámetros**:
- Delay: 5 × 250μs = 1.25ms
- Intentos: 15 por paquete

### Optimización 3: Compresión Adaptativa

**Algoritmos evaluados**:
- zlib (nivel 6): Rápido, balance compresión-velocidad
- bz2 (nivel 5): Mayor compresión, más lento
- lzma (preset 3): Máxima compresión, muy lento

**Criterios de selección**:
- Archivos < 512 bytes: Sin compresión
- Archivos 512B - 5KB: Probar zlib
- Archivos 5KB - 10KB: Probar zlib y bz2
- Archivos > 10KB: Probar zlib, bz2 y lzma
- Umbral de beneficio: Mínimo 10% de reducción

**Resultado**: Reducción promedio del 30-60% en tamaño de archivos de texto

### Optimización 4: FEC Reed-Solomon

**Implementación**: Códigos RS(32,28) sobre cada trama

**Capacidad**:
- Detección: Hasta 4 errores por trama
- Corrección: Hasta 2 errores por trama

**Resultado**: Reducción de retransmisiones en ambientes con ruido RF

### Optimización 5: Tamaño de Ráfaga

**Valor óptimo**: 15 paquetes por ráfaga

**Evaluación**: Se probaron valores de 5, 10, 15, 20 y 30 paquetes.

**Resultado**: 15 paquetes proporciona el mejor balance entre throughput y gestión de buffers del hardware.

### Optimización 6: Medición Precisa de Tiempo

**Implementación**:
- Inicio de cronómetro: Al recibir primer paquete (no al iniciar modo)
- Salida inmediata: Al completar transferencia (sin esperar timeouts)

**Resultado**: Mediciones precisas del throughput real del sistema

---

## Sistema de Logs

### Configuración de Logs

El sistema implementa logging rotativo para gestión eficiente del espacio en disco:

**Ubicación**: `/home/pi/nrf24-transmision/nrf24_daemon.log`

**Configuración**:
- Tamaño máximo por archivo: 5 MB
- Número de backups: 3
- Tamaño total máximo: 20 MB

**Formato**:
```
YYYY-MM-DD HH:MM:SS - NIVEL - Mensaje
```

### Niveles de Log

| Nivel | Descripción | Uso |
|-------|-------------|-----|
| INFO | Información general | Eventos normales del sistema |
| WARNING | Advertencias | Situaciones anómalas no críticas |
| ERROR | Errores | Fallos que requieren atención |
| DEBUG | Depuración | Información detallada (deshabilitado por defecto) |

### Ejemplo de Log

```
2025-12-01 10:30:15 - INFO - ======================================================================
2025-12-01 10:30:15 - INFO - INICIANDO DAEMON nRF24L01+
2025-12-01 10:30:15 - INFO - ======================================================================
2025-12-01 10:30:15 - INFO - Inicializando radio nRF24L01+...
2025-12-01 10:30:16 - INFO - Radio inicializado correctamente
2025-12-01 10:30:16 - INFO - CE Pin: 22
2025-12-01 10:30:16 - INFO - CSN Pin: 0
2025-12-01 10:30:16 - INFO - Canal: 90
2025-12-01 10:30:16 - INFO - Data Rate: 2 MBPS
2025-12-01 10:30:16 - INFO - Inicializando LEDs...
2025-12-01 10:30:16 - INFO - LEDs inicializados
2025-12-01 10:30:16 - INFO - Inicializando botón...
2025-12-01 10:30:16 - INFO - Botón inicializado
2025-12-01 10:30:16 - INFO - Sistema inicializado y listo
2025-12-01 10:30:16 - INFO - Esperando pulsación de botón...
2025-12-01 10:35:22 - INFO - BOTÓN LARGO - Iniciando TRANSMISIÓN MÚLTIPLE (TX-MULTI)
2025-12-01 10:35:22 - INFO - MODO TRANSMISIÓN MÚLTIPLE ACTIVADO
2025-12-01 10:35:23 - INFO - Directorio: /home/pi/nrf24-transmision/Textos
2025-12-01 10:35:23 - INFO - Archivos encontrados: 5
2025-12-01 10:35:23 - INFO - Transmitiendo archivo 1/5: archivo_01.txt
2025-12-01 10:35:28 - INFO - archivo_01.txt transmitido exitosamente
```

### Consulta de Logs

**Ver en tiempo real**:
```bash
tail -f ~/nrf24-transmision/nrf24_daemon.log
```

**Ver últimas N líneas**:
```bash
tail -n 100 ~/nrf24-transmision/nrf24_daemon.log
```

**Buscar errores**:
```bash
grep ERROR ~/nrf24-transmision/nrf24_daemon.log
```

**Logs del sistema (journalctl)**:
```bash
sudo journalctl -u nrf24-daemon -f
sudo journalctl -u nrf24-daemon --since today
sudo journalctl -u nrf24-daemon -p err
```

---

## Solución de Problemas

### Problema: El daemon no inicia

**Síntomas**: LED verde no parpadea, systemctl muestra estado "failed"

**Diagnóstico**:
```bash
sudo systemctl status nrf24-daemon
sudo journalctl -u nrf24-daemon -n 50
```

**Soluciones**:
1. Verificar que el archivo sea ejecutable:
   ```bash
   chmod +x /home/pi/nrf24-transmision/nrf24_daemon.py
   ```

2. Verificar dependencias Python:
   ```bash
   python3 -c "import pyrf24, reedsolo, RPi.GPIO"
   ```

3. Verificar conexiones del módulo nRF24L01+

4. Ejecutar manualmente para ver errores:
   ```bash
   cd /home/pi/nrf24-transmision
   python3 nrf24_daemon.py
   ```

### Problema: El botón no responde

**Síntomas**: Presionar botón no cambia el estado del LED

**Diagnóstico**:
```bash
# Verificar que el daemon esté corriendo
sudo systemctl is-active nrf24-daemon

# Ver logs del botón
tail -f ~/nrf24-transmision/nrf24_daemon.log | grep BOTÓN
```

**Soluciones**:
1. Verificar permisos GPIO:
   ```bash
   groups pi | grep gpio
   # Si no aparece, ejecutar:
   sudo usermod -a -G gpio pi
   # Cerrar sesión y volver a entrar
   ```

2. Verificar conexión física del botón (GPIO 17 - 3.3V)

3. Probar con multímetro: Verificar continuidad al presionar

### Problema: Error al inicializar radio

**Síntomas**: Log muestra "Error al inicializar nRF24L01+"

**Diagnóstico**:
```bash
# Verificar SPI
ls -l /dev/spidev0.0

# Verificar permisos SPI
groups pi | grep spi
```

**Soluciones**:
1. Habilitar SPI:
   ```bash
   sudo raspi-config
   # Navegar a: Interface Options -> SPI -> Enable
   sudo reboot
   ```

2. Verificar conexiones físicas del nRF24L01+:
   - VCC conectado a 3.3V (NUNCA 5V)
   - GND conectado correctamente
   - CE a GPIO 22
   - CSN a GPIO 0

3. Agregar capacitor de desacoplamiento (10-100μF) cerca del módulo

4. Verificar que el módulo no esté dañado (probar con otro)

### Problema: Transmisión lenta o con errores

**Síntomas**: Throughput significativamente menor a 32 KiB/s

**Diagnóstico**:
```bash
# Ver estadísticas de transmisión en logs
grep "Throughput" ~/nrf24-transmision/nrf24_daemon.log
```

**Soluciones**:
1. Reducir distancia entre transmisor y receptor

2. Verificar interferencias RF:
   - Alejar de WiFi (cambiar canal del nRF24 si es necesario)
   - Alejar de fuentes de ruido electromagnético

3. Verificar calidad de alimentación:
   - Usar fuente de alimentación de calidad
   - Agregar capacitores de desacoplamiento

4. Verificar que FEC esté habilitado:
   ```bash
   python3 -c "from fec import is_fec_available; print(is_fec_available())"
   ```

### Problema: Logs muy grandes

**Síntomas**: Espacio en disco reducido

**Diagnóstico**:
```bash
du -h ~/nrf24-transmision/nrf24_daemon.log*
```

**Soluciones**:
El sistema ya implementa rotación automática, pero para limpieza manual:

```bash
# Limpiar logs antiguos (backups)
rm ~/nrf24-transmision/nrf24_daemon.log.*

# Limpiar log actual (CUIDADO: pérdida de datos)
> ~/nrf24-transmision/nrf24_daemon.log
```

### Problema: El servicio se reinicia constantemente

**Síntomas**: systemctl muestra reinicios frecuentes

**Diagnóstico**:
```bash
sudo journalctl -u nrf24-daemon --since "10 minutes ago"
```

**Soluciones**:
1. Identificar error recurrente en logs

2. Verificar estabilidad del hardware (temperatura, alimentación)

3. Deshabilitar temporalmente para debug manual:
   ```bash
   sudo systemctl stop nrf24-daemon
   sudo systemctl disable nrf24-daemon
   cd /home/pi/nrf24-transmision
   python3 nrf24_daemon.py
   ```

4. Verificar límites de recursos:
   ```bash
   systemctl show nrf24-daemon | grep -E "Memory|CPU"
   ```

---

## Especificaciones Técnicas

### Rendimiento del Sistema

| Métrica | Valor | Notas |
|---------|-------|-------|
| Throughput máximo | 32 KiB/s | Archivos sin comprimir |
| Throughput efectivo | 25-30 KiB/s | Promedio en uso real |
| Data rate físico | 2 Mbps | Capa física nRF24L01+ |
| Eficiencia de transmisión | 99-100% | Sin pérdidas en ambiente controlado |
| Latencia de inicio | < 1 segundo | Desde pulsación hasta transmisión |
| Tiempo de cambio de modo | < 0.5 segundos | Entre TX/RX/IDLE |

### Características del Protocolo

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| Tamaño de trama | 32 bytes | Fijo, límite del hardware |
| Header | 6 bytes | file_id, seq_id, data_len, flags |
| Payload sin FEC | 26 bytes | Datos útiles |
| Payload con FEC | 22 bytes | Datos útiles + 4 bytes paridad |
| Canal RF | 90 | Configurable, evita WiFi |
| Potencia de transmisión | MAX | PA_MAX del nRF24L01+ |
| Auto-retry hardware | 15 intentos | Delay: 1.25ms |
| Timeout global | 120 segundos | Recepción |
| Timeout idle | 10 segundos | Entre paquetes |

### Compresión

| Algoritmo | Nivel | Velocidad | Ratio Típico | Uso |
|-----------|-------|-----------|--------------|-----|
| zlib | 6 | Rápida | 40-60% | Archivos generales |
| bz2 | 5 | Media | 50-70% | Archivos > 5KB |
| lzma | 3 | Lenta | 60-80% | Archivos > 10KB |

### Forward Error Correction

| Parámetro | Valor |
|-----------|-------|
| Código | Reed-Solomon RS(32,28) |
| Símbolos de datos | 28 bytes |
| Símbolos de paridad | 4 bytes |
| Capacidad de detección | 4 errores |
| Capacidad de corrección | 2 errores |
| Overhead | 14.3% |

### Recursos del Sistema

| Recurso | IDLE | Transmisión | Recepción |
|---------|------|-------------|-----------|
| CPU | < 1% | 15-25% | 10-20% |
| RAM | ~20 MB | ~40 MB | ~35 MB |
| CPU máxima (límite) | 50% | 50% | 50% |
| RAM máxima (límite) | 256 MB | 256 MB | 256 MB |

### Configuración de GPIO

| Componente | GPIO | Dirección | Pull |
|------------|------|-----------|------|
| LED Verde | 23 | OUT | - |
| LED Amarillo | 24 | OUT | - |
| LED Rojo | 25 | OUT | - |
| Botón | 17 | IN | DOWN |
| nRF24 CE | 22 | OUT | - |
| nRF24 CSN | 0 | OUT | - |

---

## Referencias

### Documentación de Hardware

1. Nordic Semiconductor nRF24L01+ Product Specification
   https://www.nordicsemi.com/products/nrf24l01

2. Raspberry Pi GPIO Documentation
   https://www.raspberrypi.com/documentation/computers/raspberry-pi.html

3. SPI Protocol Specification
   https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#serial-peripheral-interface-spi

### Bibliotecas Utilizadas

1. pyrf24 - Python wrapper for nRF24L01+
   https://github.com/nRF24/RF24

2. reedsolo - Pure-Python Reed-Solomon encoder/decoder
   https://github.com/tomerfiliba/reedsolomon

3. RPi.GPIO - Python library for Raspberry Pi GPIO
   https://sourceforge.net/projects/raspberry-gpio-python/

### systemd

1. systemd Service Management
   https://www.freedesktop.org/software/systemd/man/systemd.service.html

2. systemd Unit Configuration
   https://www.freedesktop.org/software/systemd/man/systemd.unit.html

### Compresión y FEC

1. zlib Compression Library
   https://zlib.net/

2. bzip2 Compression Library
   https://sourceware.org/bzip2/

3. LZMA/XZ Utils
   https://tukaani.org/xz/

4. Reed-Solomon Error Correction
   Reed, I. S.; Solomon, G. (1960). "Polynomial Codes Over Certain Finite Fields"

### Protocolos de Comunicación

1. Stop-and-Wait ARQ
   Tanenbaum, A. S. (2003). "Computer Networks"

2. Selective Repeat ARQ
   Peterson, L. L.; Davie, B. S. (2011). "Computer Networks: A Systems Approach"

}
---

## Apéndices

### Apéndice A: Comandos de Referencia Rápida

```bash
# Instalación
sudo ./install_daemon.sh

# Control del daemon
./daemon_control.sh status
./daemon_control.sh logs
./daemon_control.sh restart

# Systemd
sudo systemctl status nrf24-daemon
sudo systemctl restart nrf24-daemon
sudo journalctl -u nrf24-daemon -f

# Logs
tail -f ~/nrf24-transmision/nrf24_daemon.log
grep ERROR ~/nrf24-transmision/nrf24_daemon.log

# Archivos de prueba
python3 generar_archivos_prueba.py --num 5
python3 generar_archivos_prueba.py --list
python3 generar_archivos_prueba.py --clean

# Verificación
ls /dev/spidev0.0
groups pi | grep -E "spi|gpio"
```

### Apéndice B: Configuración del Archivo de Servicio

Contenido de `/etc/systemd/system/nrf24-daemon.service`:

```ini
[Unit]
Description=nRF24L01+ Transmission System Daemon
After=network.target
Documentation=https://github.com/tu-repo/nrf24-system

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/home/pi/nrf24-transmision
ExecStart=/usr/bin/python3 /home/pi/nrf24-transmision/nrf24_daemon.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

# Límites de recursos
MemoryLimit=256M
CPUQuota=50%

# Permisos
SupplementaryGroups=spi gpio

# Seguridad
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

### Apéndice C: Valores de Constantes

Archivo `constants.py`:

```python
# GPIO Pines
BUTTON_PIN = 17
LED_GREEN = 23
LED_YELLOW = 24
LED_RED = 25

# nRF24L01+ Configuración
CE_PIN = 22
CSN_PIN = 0
ADDR_A = b"\xE7\xE7\xE7\xE7\xE7"
ADDR_B = b"\xD7\xD7\xD7\xD7\xD7"

# Parámetros de Trama
FRAME_SIZE = 32
HEADER_SIZE = 6
DATA_BYTES = 26
FEC_SYMBOLS = 4
EFFECTIVE_DATA_BYTES = 22

# TX Optimización
MAX_RETRIES = 3
RETRY_DELAY = 0.04
ACK_TIMEOUT = 1.5
MAX_ROUNDS = 20
BURST_SIZE = 15
INTER_PACKET_DELAY = 0

# RX Tiempos
GLOBAL_TIMEOUT = 120
IDLE_TIMEOUT = 10

# Flags
FLAG_LAST = 0x01
FLAG_COMPRESSED = 0x02
FLAG_FEC = 0x08

# Compresión
COMPRESS_NONE = 0
COMPRESS_ZLIB = 1
COMPRESS_BZ2 = 2
COMPRESS_LZMA = 3
```

---

Fin del documento.