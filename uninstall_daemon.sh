#!/bin/bash
#
# Script de desinstalación del daemon nRF24L01+
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

INSTALL_DIR="/home/pi/nrf24-transmision"
SERVICE_NAME="nrf24-daemon"

echo -e "${RED}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${RED}║                                                           ║${NC}"
echo -e "${RED}║        DESINSTALADOR DEL DAEMON nRF24L01+                ║${NC}"
echo -e "${RED}║                                                           ║${NC}"
echo -e "${RED}╚═══════════════════════════════════════════════════════════╝${NC}\n"

# Verificar que se ejecuta como root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}✗ Este script debe ejecutarse como root${NC}"
    echo -e "${YELLOW}  Usa: sudo ./uninstall_daemon.sh${NC}\n"
    exit 1
fi

echo -e "${YELLOW}⚠️  ADVERTENCIA: Esta acción eliminará:${NC}"
echo -e "  • El servicio systemd"
echo -e "  • Los archivos del sistema"
echo -e "  • Los logs"
echo -e "  • Los archivos en $INSTALL_DIR"
echo

read -p "¿Estás seguro de que deseas continuar? (s/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Ss]$ ]]; then
    echo -e "${GREEN}Desinstalación cancelada${NC}\n"
    exit 0
fi

echo -e "\n${GREEN}▶ Paso 1: Deteniendo servicio...${NC}"
if systemctl is-active --quiet $SERVICE_NAME; then
    systemctl stop $SERVICE_NAME
    echo -e "${GREEN}  ✓ Servicio detenido${NC}"
else
    echo -e "${YELLOW}  ℹ Servicio no está corriendo${NC}"
fi

echo -e "\n${GREEN}▶ Paso 2: Deshabilitando servicio...${NC}"
if systemctl is-enabled --quiet $SERVICE_NAME 2>/dev/null; then
    systemctl disable $SERVICE_NAME
    echo -e "${GREEN}  ✓ Servicio deshabilitado${NC}"
else
    echo -e "${YELLOW}  ℹ Servicio no está habilitado${NC}"
fi

echo -e "\n${GREEN}▶ Paso 3: Eliminando archivo de servicio...${NC}"
if [ -f "/etc/systemd/system/$SERVICE_NAME.service" ]; then
    rm "/etc/systemd/system/$SERVICE_NAME.service"
    systemctl daemon-reload
    echo -e "${GREEN}  ✓ Archivo de servicio eliminado${NC}"
else
    echo -e "${YELLOW}  ℹ Archivo de servicio no encontrado${NC}"
fi

echo -e "\n${GREEN}▶ Paso 4: Preguntando sobre archivos...${NC}"
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}¿Deseas eliminar también los archivos del sistema?${NC}"
    echo -e "${YELLOW}Esto incluye: código, logs, archivos recibidos y textos${NC}"
    read -p "¿Eliminar archivos? (s/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        # Hacer backup antes de eliminar
        BACKUP_FILE="/tmp/nrf24-backup-$(date +%Y%m%d-%H%M%S).tar.gz"
        echo -e "${BLUE}  Creando backup en: $BACKUP_FILE${NC}"
        tar -czf "$BACKUP_FILE" -C "$(dirname $INSTALL_DIR)" "$(basename $INSTALL_DIR)" 2>/dev/null || true
        
        rm -rf "$INSTALL_DIR"
        echo -e "${GREEN}  ✓ Archivos eliminados${NC}"
        echo -e "${GREEN}  ✓ Backup guardado en: $BACKUP_FILE${NC}"
    else
        echo -e "${YELLOW}  ⏸ Archivos conservados en: $INSTALL_DIR${NC}"
    fi
else
    echo -e "${YELLOW}  ℹ Directorio no encontrado: $INSTALL_DIR${NC}"
fi

echo -e "\n${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                           ║${NC}"
echo -e "${BLUE}║           ✓ DESINSTALACIÓN COMPLETADA                    ║${NC}"
echo -e "${BLUE}║                                                           ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}\n"

echo -e "${GREEN}El daemon ha sido desinstalado.${NC}"
echo -e "${YELLOW}Para reinstalar, ejecuta: sudo ./install_daemon.sh${NC}\n"