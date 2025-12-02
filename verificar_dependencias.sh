#!/bin/bash
#
# Script de diagnóstico para verificar dependencias de Python
# Verifica que todas las bibliotecas necesarias estén instaladas correctamente
# Versión con soporte para entorno virtual
#

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Detectar directorio del script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
VENV_PATH="$SCRIPT_DIR/.venv"

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                           ║${NC}"
echo -e "${BLUE}║        DIAGNÓSTICO DE DEPENDENCIAS nRF24L01+             ║${NC}"
echo -e "${BLUE}║              (Versión con entorno virtual)                ║${NC}"
echo -e "${BLUE}║                                                           ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}\n"

# Verificar si existe entorno virtual
echo -e "${GREEN}▶ Verificando entorno virtual...${NC}\n"
echo -n -e "Entorno virtual en $VENV_PATH... "
if [ -d "$VENV_PATH" ]; then
    echo -e "${GREEN}✓ ENCONTRADO${NC}"
    USE_VENV=true
    PYTHON_CMD="$VENV_PATH/bin/python"
    PIP_CMD="$VENV_PATH/bin/pip"
else
    echo -e "${YELLOW}✗ NO ENCONTRADO${NC}"
    echo -e "${YELLOW}  Usando Python del sistema${NC}"
    USE_VENV=false
    PYTHON_CMD="python3"
    PIP_CMD="pip3"
fi
echo

# Función para verificar módulo
check_module() {
    local module=$1
    local import_name=$2
    
    echo -n -e "Verificando ${YELLOW}$module${NC}... "
    
    if $PYTHON_CMD -c "import $import_name" 2>/dev/null; then
        echo -e "${GREEN}✓ OK${NC}"
        
        # Obtener versión si es posible
        version=$($PYTHON_CMD -c "import $import_name; print(getattr($import_name, '__version__', 'N/A'))" 2>/dev/null)
        if [ "$version" != "N/A" ]; then
            echo -e "  Versión: $version"
        fi
        
        # Obtener ubicación
        location=$($PYTHON_CMD -c "import $import_name; print($import_name.__file__)" 2>/dev/null)
        echo -e "  Ubicación: $location"
        echo
        return 0
    else
        echo -e "${RED}✗ NO ENCONTRADO${NC}"
        if [ "$USE_VENV" = true ]; then
            echo -e "  ${YELLOW}Instalar con: $VENV_PATH/bin/pip install $module${NC}"
            echo -e "  ${YELLOW}o activar venv y usar: pip install $module${NC}"
        else
            echo -e "  ${YELLOW}Instalar con: pip3 install $module${NC}"
            echo -e "  ${YELLOW}o: pip3 install --break-system-packages $module${NC}"
        fi
        echo
        return 1
    fi
}

echo -e "${GREEN}▶ Verificando Python...${NC}"
$PYTHON_CMD --version
echo -e "Ejecutable: $(which $PYTHON_CMD)"
if [ "$USE_VENV" = true ]; then
    echo -e "Tipo: ${GREEN}Entorno virtual${NC}"
else
    echo -e "Tipo: ${YELLOW}Sistema${NC}"
fi
echo

echo -e "${GREEN}▶ Verificando pip...${NC}"
if command -v $PIP_CMD &> /dev/null; then
    $PIP_CMD --version
    echo -e "Ejecutable: $(which $PIP_CMD)"
else
    echo -e "${RED}✗ pip no encontrado${NC}"
fi
echo

echo -e "${GREEN}▶ Verificando módulos Python requeridos...${NC}\n"

# Verificar cada módulo
errors=0

check_module "pyrf24" "RF24" || ((errors++))
check_module "reedsolo" "reedsolo" || ((errors++))
check_module "RPi.GPIO" "RPi.GPIO" || ((errors++))

echo -e "${GREEN}▶ Verificando acceso a hardware...${NC}\n"

# Verificar SPI
echo -n -e "SPI habilitado... "
if [ -e /dev/spidev0.0 ]; then
    echo -e "${GREEN}✓ OK${NC}"
    ls -l /dev/spidev0.0
else
    echo -e "${RED}✗ NO${NC}"
    echo -e "  ${YELLOW}Habilitar con: sudo raspi-config${NC}"
    echo -e "  ${YELLOW}Interfacing Options -> SPI -> Enable${NC}"
    ((errors++))
fi
echo

# Verificar GPIO
echo -n -e "GPIO accesible... "
if [ -d /sys/class/gpio ]; then
    echo -e "${GREEN}✓ OK${NC}"
    ls -ld /sys/class/gpio
else
    echo -e "${RED}✗ NO${NC}"
    ((errors++))
fi
echo

# Verificar permisos del usuario
echo -e "${GREEN}▶ Verificando permisos del usuario...${NC}\n"

current_user=$(whoami)
echo "Usuario actual: $current_user"
echo -n "Grupos: "
groups $current_user

echo
echo -n -e "Grupo 'spi'... "
if groups $current_user | grep -q '\bspi\b'; then
    echo -e "${GREEN}✓ OK${NC}"
else
    echo -e "${RED}✗ NO${NC}"
    echo -e "  ${YELLOW}Agregar con: sudo usermod -a -G spi $current_user${NC}"
    ((errors++))
fi

echo -n -e "Grupo 'gpio'... "
if groups $current_user | grep -q '\bgpio\b'; then
    echo -e "${GREEN}✓ OK${NC}"
else
    echo -e "${RED}✗ NO${NC}"
    echo -e "  ${YELLOW}Agregar con: sudo usermod -a -G gpio $current_user${NC}"
    ((errors++))
fi
echo

# Verificar PATH
echo -e "${GREEN}▶ Verificando PATH...${NC}\n"
echo "PATH actual:"
echo "$PATH" | tr ':' '\n' | while read dir; do echo "  - $dir"; done
echo

# Probar importación completa
echo -e "${GREEN}▶ Prueba de importación completa...${NC}\n"
$PYTHON_CMD << 'EOF'
import sys
print("Python path:")
for p in sys.path:
    print(f"  - {p}")
print()

try:
    from pyrf24 import RF24
    print("✓ RF24 importado correctamente")
    print(f"  RF24: {RF24}")
except Exception as e:
    print(f"✗ Error al importar RF24: {e}")
    sys.exit(1)

try:
    import reedsolo
    print("✓ reedsolo importado correctamente")
except Exception as e:
    print(f"✗ Error al importar reedsolo: {e}")
    sys.exit(1)

try:
    import RPi.GPIO as GPIO
    print("✓ RPi.GPIO importado correctamente")
except Exception as e:
    print(f"✗ Error al importar RPi.GPIO: {e}")
    sys.exit(1)

print("\n✓ Todas las importaciones exitosas")
EOF

import_status=$?
echo

# Resumen final
echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                           ║${NC}"

if [ $errors -eq 0 ] && [ $import_status -eq 0 ]; then
    echo -e "${BLUE}║              ${GREEN}✓ SISTEMA CONFIGURADO CORRECTAMENTE${BLUE}         ║${NC}"
    echo -e "${BLUE}║                                                           ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}\n"
    echo -e "${GREEN}El daemon debería funcionar correctamente.${NC}\n"
    exit 0
else
    echo -e "${BLUE}║              ${RED}✗ SE ENCONTRARON $errors ERROR(ES)${BLUE}               ║${NC}"
    echo -e "${BLUE}║                                                           ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}\n"
    echo -e "${YELLOW}Corrige los errores indicados arriba y vuelve a ejecutar este script.${NC}\n"
    
    if [ $current_user != "root" ]; then
        echo -e "${YELLOW}Nota: Si agregaste el usuario a nuevos grupos, cierra sesión y vuelve a entrar.${NC}\n"
    fi
    
    exit 1
fi
