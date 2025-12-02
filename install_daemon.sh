#!/bin/bash
#
# Script de instalación del daemon nRF24L01+
# Configura el sistema para ejecutarse automáticamente al iniciar
#

set -e  # Salir si hay errores

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuración
INSTALL_DIR="/home/pi/nrf24-transmision"
SERVICE_FILE="nrf24-daemon.service"
DAEMON_SCRIPT="nrf24_daemon.py"
USER="pi"

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                           ║${NC}"
echo -e "${BLUE}║        INSTALADOR DEL DAEMON nRF24L01+                   ║${NC}"
echo -e "${BLUE}║                                                           ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}\n"

# Verificar que se ejecuta como root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}✗ Este script debe ejecutarse como root${NC}"
    echo -e "${YELLOW}  Usa: sudo ./install_daemon.sh${NC}\n"
    exit 1
fi

echo -e "${GREEN}▶ Paso 1: Verificando sistema...${NC}"

# Verificar que estamos en una Raspberry Pi
if [ ! -f /proc/device-tree/model ]; then
    echo -e "${YELLOW}⚠ Advertencia: No se detectó Raspberry Pi${NC}"
    read -p "¿Continuar de todas formas? (s/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        exit 1
    fi
fi

# Verificar Python 3
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 no está instalado${NC}"
    exit 1
fi
echo -e "${GREEN}  ✓ Python 3 encontrado: $(python3 --version)${NC}"

# Verificar SPI
if [ ! -e /dev/spidev0.0 ]; then
    echo -e "${YELLOW}⚠ SPI no está habilitado${NC}"
    echo -e "${YELLOW}  Habilitando SPI...${NC}"
    raspi-config nonint do_spi 0
    echo -e "${GREEN}  ✓ SPI habilitado (requiere reinicio)${NC}"
fi

echo -e "\n${GREEN}▶ Paso 2: Creando directorios...${NC}"

# Crear directorio de instalación
if [ ! -d "$INSTALL_DIR" ]; then
    mkdir -p "$INSTALL_DIR"
    echo -e "${GREEN}  ✓ Directorio creado: $INSTALL_DIR${NC}"
else
    echo -e "${YELLOW}  ℹ Directorio ya existe: $INSTALL_DIR${NC}"
fi

# Crear subdirectorios
mkdir -p "$INSTALL_DIR/Textos"
mkdir -p "$INSTALL_DIR/recibidos"
echo -e "${GREEN}  ✓ Subdirectorios creados${NC}"

echo -e "\n${GREEN}▶ Paso 3: Copiando archivos...${NC}"

# Copiar archivos Python
PYTHON_FILES="compression.py constants.py fec.py frame_handler.py hardware.py radio_config.py receiver.py transmitter.py nrf24_daemon.py generar_archivos_prueba.py"

for file in $PYTHON_FILES; do
    if [ -f "$file" ]; then
        cp "$file" "$INSTALL_DIR/"
        echo -e "${GREEN}  ✓ Copiado: $file${NC}"
    else
        echo -e "${RED}  ✗ No encontrado: $file${NC}"
    fi
done

# Hacer ejecutable el daemon
chmod +x "$INSTALL_DIR/$DAEMON_SCRIPT"
chmod +x "$INSTALL_DIR/generar_archivos_prueba.py"

echo -e "\n${GREEN}▶ Paso 4: Configurando permisos...${NC}"

# Cambiar propietario
chown -R $USER:$USER "$INSTALL_DIR"
echo -e "${GREEN}  ✓ Propietario configurado: $USER${NC}"

# Agregar usuario a grupos necesarios
usermod -a -G spi,gpio $USER
echo -e "${GREEN}  ✓ Usuario agregado a grupos: spi, gpio${NC}"

echo -e "\n${GREEN}▶ Paso 5: Instalando dependencias Python...${NC}"

# Instalar dependencias como usuario pi
su - $USER -c "pip3 install --user pyrf24 reedsolo RPi.GPIO" 2>&1 | grep -E "(Successfully|already satisfied)" || true
echo -e "${GREEN}  ✓ Dependencias instaladas${NC}"

echo -e "\n${GREEN}▶ Paso 6: Configurando servicio systemd...${NC}"

# Copiar archivo de servicio
if [ -f "$SERVICE_FILE" ]; then
    # Actualizar rutas en el archivo de servicio
    sed -i "s|WorkingDirectory=.*|WorkingDirectory=$INSTALL_DIR|g" "$SERVICE_FILE"
    sed -i "s|ExecStart=.*|ExecStart=/usr/bin/python3 $INSTALL_DIR/$DAEMON_SCRIPT|g" "$SERVICE_FILE"
    sed -i "s|User=.*|User=$USER|g" "$SERVICE_FILE"
    sed -i "s|Group=.*|Group=$USER|g" "$SERVICE_FILE"
    
    cp "$SERVICE_FILE" /etc/systemd/system/
    echo -e "${GREEN}  ✓ Archivo de servicio copiado${NC}"
else
    echo -e "${RED}  ✗ Archivo de servicio no encontrado: $SERVICE_FILE${NC}"
    exit 1
fi

# Recargar systemd
systemctl daemon-reload
echo -e "${GREEN}  ✓ Systemd recargado${NC}"

# Habilitar servicio para inicio automático
systemctl enable nrf24-daemon.service
echo -e "${GREEN}  ✓ Servicio habilitado para inicio automático${NC}"

echo -e "\n${GREEN}▶ Paso 7: Creando archivos de prueba...${NC}"

# Crear archivos de prueba como usuario pi
su - $USER -c "cd $INSTALL_DIR && python3 generar_archivos_prueba.py --num 3" > /dev/null 2>&1
echo -e "${GREEN}  ✓ Archivos de prueba creados en $INSTALL_DIR/Textos/${NC}"

echo -e "\n${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                           ║${NC}"
echo -e "${BLUE}║              ✓ INSTALACIÓN COMPLETADA                    ║${NC}"
echo -e "${BLUE}║                                                           ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}\n"

echo -e "${GREEN}📁 Archivos instalados en:${NC} $INSTALL_DIR"
echo -e "${GREEN}📋 Servicio configurado:${NC} nrf24-daemon.service"
echo -e "${GREEN}📊 Log del sistema:${NC} $INSTALL_DIR/nrf24_daemon.log\n"

echo -e "${YELLOW}⚙️  COMANDOS ÚTILES:${NC}\n"
echo -e "  ${BLUE}# Iniciar el servicio ahora:${NC}"
echo -e "    sudo systemctl start nrf24-daemon\n"
echo -e "  ${BLUE}# Ver estado del servicio:${NC}"
echo -e "    sudo systemctl status nrf24-daemon\n"
echo -e "  ${BLUE}# Ver logs en tiempo real:${NC}"
echo -e "    tail -f $INSTALL_DIR/nrf24_daemon.log\n"
echo -e "  ${BLUE}# Ver logs del sistema:${NC}"
echo -e "    sudo journalctl -u nrf24-daemon -f\n"
echo -e "  ${BLUE}# Detener el servicio:${NC}"
echo -e "    sudo systemctl stop nrf24-daemon\n"
echo -e "  ${BLUE}# Deshabilitar inicio automático:${NC}"
echo -e "    sudo systemctl disable nrf24-daemon\n"

echo -e "${YELLOW}🎮 CONTROL:${NC}"
echo -e "  • Pulsación CORTA (< 1s):  TX (archivo único)"
echo -e "  • Pulsación MEDIA (1-3s):  RX (receptor)"
echo -e "  • Pulsación LARGA (≥ 3s):  TX-MULTI (múltiples archivos)\n"

# Preguntar si iniciar el servicio ahora
read -p "¿Deseas iniciar el servicio ahora? (S/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Nn]$ ]]; then
    echo -e "${YELLOW}⏸  Servicio no iniciado. Usa: sudo systemctl start nrf24-daemon${NC}"
    echo -e "${YELLOW}⚠  O reinicia el sistema para que inicie automáticamente${NC}\n"
else
    systemctl start nrf24-daemon
    sleep 2
    if systemctl is-active --quiet nrf24-daemon; then
        echo -e "${GREEN}✓ Servicio iniciado exitosamente${NC}\n"
        echo -e "${BLUE}Estado del servicio:${NC}"
        systemctl status nrf24-daemon --no-pager | head -n 15
    else
        echo -e "${RED}✗ Error al iniciar el servicio${NC}"
        echo -e "${YELLOW}Ver logs con: sudo journalctl -u nrf24-daemon -n 50${NC}\n"
    fi
fi

echo -e "\n${GREEN}¡Sistema listo! El daemon se ejecutará automáticamente al iniciar.${NC}\n"