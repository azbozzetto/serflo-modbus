"""
Sistema de logging para datos del HP550 Hydramotion
Gestiona el logging de lecturas y errores con rotación de archivos
"""

import logging
from logging.handlers import RotatingFileHandler
import csv
import os
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path


class HP550DataLogger:
    """
    Logger para datos del HP550 con soporte para archivos de log y CSV.
    """

    def __init__(
        self,
        log_file: str = "logs/hp550.log",
        log_level: str = "INFO",
        max_bytes: int = 10485760,  # 10 MB
        backup_count: int = 5,
        csv_output: Optional[str] = None
    ):
        """
        Inicializa el logger.

        Args:
            log_file: Ruta del archivo de log
            log_level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            max_bytes: Tamaño máximo del archivo de log antes de rotar
            backup_count: Número de archivos de backup a mantener
            csv_output: Ruta opcional para exportar datos a CSV
        """
        self.log_file = log_file
        self.csv_output = csv_output

        # Crear directorio de logs si no existe
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # Configurar logger
        self.logger = logging.getLogger("HP550")
        self.logger.setLevel(getattr(logging, log_level.upper()))

        # Limpiar handlers existentes
        self.logger.handlers.clear()

        # Handler para archivo con rotación
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

        # Handler para consola
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # Inicializar CSV si se especificó
        if self.csv_output:
            self._initialize_csv()

        self.logger.info("HP550 Data Logger initialized")

    def _initialize_csv(self):
        """
        Inicializa el archivo CSV si no existe.
        """
        csv_dir = os.path.dirname(self.csv_output)
        if csv_dir and not os.path.exists(csv_dir):
            os.makedirs(csv_dir)

        # Si el archivo no existe, crear con encabezados
        if not os.path.exists(self.csv_output):
            with open(self.csv_output, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp',
                    'cycle_counter',
                    'vl_average',
                    'vc_average',
                    'vn_average',
                    'temperature',
                    'v_live',
                    'vl_live',
                    'vc_live',
                    'vn_live',
                    'alarm_low',
                    'alarm_high',
                    'battery_volts',
                    'battery_adc',
                    'is_valid',
                    'error_message'
                ])
            self.logger.info(f"CSV file created: {self.csv_output}")

    def log_reading(self, reading: Dict[str, Any], level: str = "INFO"):
        """
        Registra una lectura del HP550.

        Args:
            reading: Diccionario con los datos leídos
            level: Nivel de log (INFO, WARNING, ERROR)
        """
        log_method = getattr(self.logger, level.lower())

        # Log básico
        vl = reading.get('vl_average')
        vc = reading.get('vc_average')
        temp = reading.get('temperature')

        vl_str = f"{vl:.2f}" if vl is not None else "N/A"
        vc_str = f"{vc:.2f}" if vc is not None else "N/A"
        temp_str = f"{temp:.1f}" if temp is not None else "N/A"

        msg = (
            f"Reading - VL: {vl_str} cP, "
            f"VC: {vc_str} cP, "
            f"Temp: {temp_str} °C, "
            f"Valid: {reading.get('is_valid', True)}"
        )
        log_method(msg)

        # Escribir a CSV si está configurado
        if self.csv_output:
            self._write_to_csv(reading)

    def _write_to_csv(self, reading: Dict[str, Any]):
        """
        Escribe una lectura al archivo CSV.

        Args:
            reading: Diccionario con los datos leídos
        """
        try:
            with open(self.csv_output, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    reading.get('timestamp', datetime.now().isoformat()),
                    reading.get('cycle_counter', ''),
                    reading.get('vl_average', ''),
                    reading.get('vc_average', ''),
                    reading.get('vn_average', ''),
                    reading.get('temperature', ''),
                    reading.get('v_live', ''),
                    reading.get('vl_live', ''),
                    reading.get('vc_live', ''),
                    reading.get('vn_live', ''),
                    reading.get('alarm_low', ''),
                    reading.get('alarm_high', ''),
                    reading.get('battery_volts', ''),
                    reading.get('battery_adc', ''),
                    reading.get('is_valid', True),
                    reading.get('error_message', '')
                ])
        except Exception as e:
            self.logger.error(f"Error writing to CSV: {e}")

    def log_error(self, error_message: str, exception: Optional[Exception] = None):
        """
        Registra un error.

        Args:
            error_message: Mensaje de error
            exception: Excepción opcional
        """
        if exception:
            self.logger.error(f"{error_message}: {str(exception)}", exc_info=True)
        else:
            self.logger.error(error_message)

    def log_warning(self, warning_message: str):
        """
        Registra una advertencia.

        Args:
            warning_message: Mensaje de advertencia
        """
        self.logger.warning(warning_message)

    def log_info(self, info_message: str):
        """
        Registra información general.

        Args:
            info_message: Mensaje informativo
        """
        self.logger.info(info_message)

    def log_debug(self, debug_message: str):
        """
        Registra información de debug.

        Args:
            debug_message: Mensaje de debug
        """
        self.logger.debug(debug_message)

    def log_connection_event(self, event_type: str, details: str = ""):
        """
        Registra eventos de conexión/desconexión.

        Args:
            event_type: Tipo de evento (connect, disconnect, reconnect, timeout)
            details: Detalles adicionales
        """
        msg = f"Connection event: {event_type}"
        if details:
            msg += f" - {details}"

        if event_type in ['disconnect', 'timeout', 'error']:
            self.logger.warning(msg)
        else:
            self.logger.info(msg)

    def log_invalid_reading(self, reading: Dict[str, Any], reason: str):
        """
        Registra una lectura inválida.

        Args:
            reading: Diccionario con los datos leídos
            reason: Razón por la que la lectura es inválida
        """
        self.logger.warning(f"Invalid reading: {reason} - Data: {reading}")

        # Agregar el error al reading y escribir a CSV si está configurado
        if self.csv_output:
            reading['error_message'] = reason
            reading['is_valid'] = False
            self._write_to_csv(reading)

    def close(self):
        """
        Cierra el logger y libera recursos.
        """
        self.logger.info("Closing HP550 Data Logger")
        for handler in self.logger.handlers:
            handler.close()
            self.logger.removeHandler(handler)
