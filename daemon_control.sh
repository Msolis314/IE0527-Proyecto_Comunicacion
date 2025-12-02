#!/bin/bash
#
# Script de gestión del daemon nRF24L01+
# Proporciona comandos simples para controlar el servicio
#

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SERVICE_NAME="nrf24-daemon"
LOG_FILE="/home/mariana/Documents/IE0527-Proyecto_Comunicacion/nrf24_daemon.log"

# Función para mostrar el banner
show_banner() {
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║                                                           ║${NC}"
    echo -e "${BLUE}║        GESTOR DEL DAEMON nRF24L01+                       ║${NC}"
    echo -e "${BLUE}║                                                           ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}\n"
}

# Función para mostrar el estado
show_status() {
    echo -e "${GREEN}▶ Estado del Servicio:${NC}\n"
    sudo systemctl status $SERVICE_NAME --no-pager | head -n 15
    echo
}

# Función para mostrar logs
show_logs() {
    echo -e "${GREEN}▶ Últimos logs (presiona Ctrl+C para salir):${NC}\n"
    if [ -f "$LOG_FILE" ]; then
        tail -f "$LOG_FILE"
    else
        echo -e "${RED}✗ Archivo de log no encontrado: $LOG_FILE${NC}"
    fi
}

# Función para mostrar logs históricos
show_log_history() {
    local lines=${1:-50}
    echo -e "${GREEN}▶ Últimas $lines líneas del log:${NC}\n"
    if [ -f "$LOG_FILE" ]; then
        tail -n $lines "$LOG_FILE"
    else
        echo -e "${RED}✗ Archivo de log no encontrado: $LOG_FILE${NC}"
    fi
}

# Función para iniciar el servicio
start_service() {
    echo -e "${GREEN}▶ Iniciando servicio...${NC}"
    sudo systemctl start $SERVICE_NAME
    sleep 2
    if sudo systemctl is-active --quiet $SERVICE_NAME; then
        echo -e "${GREEN}✓ Servicio iniciado exitosamente${NC}\n"
        show_status
    else
        echo -e "${RED}✗ Error al iniciar el servicio${NC}"
        echo -e "${YELLOW}Ver logs con: $0 logs${NC}\n"
    fi
}

# Función para detener el servicio
stop_service() {
    echo -e "${YELLOW}▶ Deteniendo servicio...${NC}"
    sudo systemctl stop $SERVICE_NAME
    sleep 1
    if ! sudo systemctl is-active --quiet $SERVICE_NAME; then
        echo -e "${GREEN}✓ Servicio detenido${NC}\n"
    else
        echo -e "${RED}✗ Error al detener el servicio${NC}\n"
    fi
}

# Función para reiniciar el servicio
restart_service() {
    echo -e "${YELLOW}▶ Reiniciando servicio...${NC}"
    sudo systemctl restart $SERVICE_NAME
    sleep 2
    if sudo systemctl is-active --quiet $SERVICE_NAME; then
        echo -e "${GREEN}✓ Servicio reiniciado exitosamente${NC}\n"
        show_status
    else
        echo -e "${RED}✗ Error al reiniciar el servicio${NC}\n"
    fi
}

# Función para mostrar ayuda
show_help() {
    echo -e "${BLUE}Uso:${NC} $0 {comando}\n"
    echo -e "${YELLOW}Comandos disponibles:${NC}\n"
    echo -e "  ${GREEN}status${NC}        - Ver estado del servicio"
    echo -e "  ${GREEN}start${NC}         - Iniciar el servicio"
    echo -e "  ${GREEN}stop${NC}          - Detener el servicio"
    echo -e "  ${GREEN}restart${NC}       - Reiniciar el servicio"
    echo -e "  ${GREEN}logs${NC}          - Ver logs en tiempo real"
    echo -e "  ${GREEN}history${NC}       - Ver últimos 50 logs"
    echo -e "  ${GREEN}enable${NC}        - Habilitar inicio automático"
    echo -e "  ${GREEN}disable${NC}       - Deshabilitar inicio automático"
    echo -e "  ${GREEN}help${NC}          - Mostrar esta ayuda\n"
    echo -e "${YELLOW}Ejemplos:${NC}"
    echo -e "  $0 status"
    echo -e "  $0 logs"
    echo -e "  $0 restart\n"
}

# Función para habilitar inicio automático
enable_service() {
    echo -e "${GREEN}▶ Habilitando inicio automático...${NC}"
    sudo systemctl enable $SERVICE_NAME
    echo -e "${GREEN}✓ Servicio habilitado para inicio automático${NC}\n"
}

# Función para deshabilitar inicio automático
disable_service() {
    echo -e "${YELLOW}▶ Deshabilitando inicio automático...${NC}"
    sudo systemctl disable $SERVICE_NAME
    echo -e "${YELLOW}✓ Servicio deshabilitado (no iniciará automáticamente)${NC}\n"
}

# Script principal
show_banner

case "${1:-help}" in
    status)
        show_status
        ;;
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        restart_service
        ;;
    logs)
        show_logs
        ;;
    history)
        show_log_history ${2:-50}
        ;;
    enable)
        enable_service
        ;;
    disable)
        disable_service
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}✗ Comando desconocido: $1${NC}\n"
        show_help
        exit 1
        ;;
esac

exit 0
