#!/bin/bash
#
# Script auxiliar para activar el entorno virtual del proyecto nRF24L01+
# Uso: source activate_venv.sh
#

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
VENV_DIR="$SCRIPT_DIR/.venv"

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

if [ ! -d "$VENV_DIR" ]; then
    echo -e "${RED}✗ Entorno virtual no encontrado en: $VENV_DIR${NC}"
    echo -e "${YELLOW}Ejecuta primero: python3 -m venv .venv${NC}"
    echo -e "${YELLOW}Luego: source .venv/bin/activate${NC}"
    echo -e "${YELLOW}Y finalmente: pip install pyrf24 reedsolo RPi.GPIO${NC}"
    return 1 2>/dev/null || exit 1
fi

# Activar entorno virtual
source "$VENV_DIR/bin/activate"

echo -e "${GREEN}✓ Entorno virtual activado${NC}"
echo -e "${GREEN}Python: $(which python)${NC}"
echo -e "${GREEN}Versión: $(python --version)${NC}"
echo
echo -e "${YELLOW}Para desactivar: deactivate${NC}"
