"""
Utilidades comunes para el proyecto HP550 Modbus Reader
"""

import yaml
import os
from typing import Dict, Any
from pathlib import Path


def load_config(config_path: str = "config/config.yaml") -> Dict[str, Any]:
    """
    Carga la configuración desde un archivo YAML.

    Args:
        config_path: Ruta al archivo de configuración

    Returns:
        Diccionario con la configuración

    Raises:
        FileNotFoundError: Si el archivo no existe
        yaml.YAMLError: Si hay error al parsear el YAML
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    return config


def validate_config(config: Dict[str, Any]) -> bool:
    """
    Valida que la configuración tenga todos los campos requeridos.

    Args:
        config: Diccionario con la configuración

    Returns:
        True si la configuración es válida

    Raises:
        ValueError: Si falta algún campo requerido o tiene valor inválido
    """
    required_sections = ['serial', 'modbus', 'instrument', 'logging']

    # Verificar secciones principales
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing required section: {section}")

    # Validar serial
    serial_fields = ['port', 'baudrate', 'parity', 'stopbits', 'bytesize', 'timeout']
    for field in serial_fields:
        if field not in config['serial']:
            raise ValueError(f"Missing required field: serial.{field}")

    # Validar valores de baudrate
    valid_baudrates = [1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200]
    if config['serial']['baudrate'] not in valid_baudrates:
        raise ValueError(f"Invalid baudrate: {config['serial']['baudrate']}")

    # Validar paridad
    valid_parity = ['N', 'E', 'O']
    if config['serial']['parity'] not in valid_parity:
        raise ValueError(f"Invalid parity: {config['serial']['parity']}")

    # Validar modbus
    modbus_fields = ['slave_address', 'polling_interval', 'max_retries']
    for field in modbus_fields:
        if field not in config['modbus']:
            raise ValueError(f"Missing required field: modbus.{field}")

    # Validar dirección de esclavo (1-247)
    if not 1 <= config['modbus']['slave_address'] <= 247:
        raise ValueError(f"Invalid slave address: {config['modbus']['slave_address']}")

    # Validar polling interval (mínimo 1.0 según manual HP550)
    if config['modbus']['polling_interval'] < 1.0:
        raise ValueError(f"Polling interval too low: {config['modbus']['polling_interval']}")

    # Validar instrument
    instrument_fields = ['viscosity_range', 'temperature_range']
    for field in instrument_fields:
        if field not in config['instrument']:
            raise ValueError(f"Missing required field: instrument.{field}")

    # Validar logging
    logging_fields = ['level', 'file', 'max_bytes', 'backup_count']
    for field in logging_fields:
        if field not in config['logging']:
            raise ValueError(f"Missing required field: logging.{field}")

    # Validar nivel de logging
    valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    if config['logging']['level'].upper() not in valid_levels:
        raise ValueError(f"Invalid log level: {config['logging']['level']}")

    return True


def get_default_config() -> Dict[str, Any]:
    """
    Retorna la configuración por defecto.

    Returns:
        Diccionario con configuración por defecto
    """
    return {
        'serial': {
            'port': 'COM1',
            'baudrate': 9600,
            'parity': 'E',
            'stopbits': 1,
            'bytesize': 7,
            'timeout': 2.0
        },
        'modbus': {
            'slave_address': 1,
            'polling_interval': 1.0,
            'max_retries': 3
        },
        'instrument': {
            'viscosity_range': 10000,
            'temperature_range': 500
        },
        'logging': {
            'level': 'INFO',
            'file': 'logs/hp550.log',
            'max_bytes': 10485760,
            'backup_count': 5
        }
    }


def create_default_config(output_path: str = "config/config.yaml"):
    """
    Crea un archivo de configuración por defecto.

    Args:
        output_path: Ruta donde crear el archivo
    """
    config = get_default_config()

    # Crear directorio si no existe
    config_dir = os.path.dirname(output_path)
    if config_dir and not os.path.exists(config_dir):
        os.makedirs(config_dir)

    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)


def ensure_directory_exists(directory: str):
    """
    Asegura que un directorio exista, creándolo si es necesario.

    Args:
        directory: Ruta del directorio
    """
    if not os.path.exists(directory):
        os.makedirs(directory)


def format_connection_info(info: Dict[str, Any]) -> str:
    """
    Formatea la información de conexión para impresión.

    Args:
        info: Diccionario con información de conexión

    Returns:
        String formateado
    """
    lines = [
        "=== HP550 Connection Info ===",
        f"Port: {info.get('port', 'N/A')}",
        f"Baudrate: {info.get('baudrate', 'N/A')}",
        f"Parity: {info.get('parity', 'N/A')}",
        f"Stopbits: {info.get('stopbits', 'N/A')}",
        f"Bytesize: {info.get('bytesize', 'N/A')}",
        f"Timeout: {info.get('timeout', 'N/A')} s",
        f"Slave Address: {info.get('slave_address', 'N/A')}",
        f"Connected: {info.get('connected', False)}",
        "=" * 30
    ]
    return "\n".join(lines)


def get_project_root() -> Path:
    """
    Obtiene el directorio raíz del proyecto.

    Returns:
        Path al directorio raíz
    """
    return Path(__file__).parent.parent


def resolve_path(relative_path: str) -> str:
    """
    Resuelve una ruta relativa al directorio raíz del proyecto.

    Args:
        relative_path: Ruta relativa

    Returns:
        Ruta absoluta
    """
    root = get_project_root()
    return str(root / relative_path)
