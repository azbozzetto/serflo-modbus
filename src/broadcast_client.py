"""
Cliente para recibir broadcasting del HP550 Hydramotion
Lee continuamente el stream de datos
"""

import serial
import time
from typing import Optional, Callable
from .broadcast_parser import HP550BroadcastParser


class HP550BroadcastClient:
    """
    Cliente para modo broadcasting del HP550.

    El HP550 con bE=ON transmite datos continuamente.
    Este cliente lee el stream y lo parsea.
    """

    def __init__(
        self,
        port: str,
        baudrate: int = 9600,
        parity: str = 'E',
        stopbits: int = 1,
        bytesize: int = 7,
        timeout: float = 1.0
    ):
        """
        Inicializa el cliente de broadcasting.

        Args:
            port: Puerto serial (ej: "COM9")
            baudrate: Velocidad de comunicación (default: 9600)
            parity: Paridad ('E', 'N', 'O')
            stopbits: Bits de parada (1 o 2)
            bytesize: Tamaño de datos (7 u 8)
            timeout: Timeout de lectura en segundos
        """
        self.port = port
        self.baudrate = baudrate
        self.parity = self._parse_parity(parity)
        self.stopbits = stopbits
        self.bytesize = bytesize
        self.timeout = timeout

        self.serial = None
        self.parser = HP550BroadcastParser()
        self._connected = False
        self._running = False

    def _parse_parity(self, parity: str):
        """Convierte string de paridad a constante de pyserial."""
        if parity.upper() == 'N':
            return serial.PARITY_NONE
        elif parity.upper() == 'E':
            return serial.PARITY_EVEN
        elif parity.upper() == 'O':
            return serial.PARITY_ODD
        else:
            return serial.PARITY_EVEN

    def connect(self) -> bool:
        """
        Abre la conexión serial.

        Returns:
            True si la conexión fue exitosa
        """
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                parity=self.parity,
                stopbits=self.stopbits,
                bytesize=self.bytesize,
                timeout=self.timeout
            )

            self._connected = True
            time.sleep(0.5)  # Dar tiempo a estabilizar
            return True

        except Exception as e:
            print(f"Error connecting: {e}")
            self._connected = False
            return False

    def disconnect(self):
        """Cierra la conexión serial."""
        self._running = False
        if self.serial and self.serial.is_open:
            self.serial.close()
        self._connected = False

    def is_connected(self) -> bool:
        """
        Verifica si está conectado.

        Returns:
            True si está conectado
        """
        return self._connected and self.serial and self.serial.is_open

    def read_once(self, buffer_size: int = 512) -> Optional[bytes]:
        """
        Lee una vez del buffer serial.

        Args:
            buffer_size: Tamaño máximo a leer

        Returns:
            Bytes leídos o None si hay error
        """
        if not self.is_connected():
            return None

        try:
            if self.serial.in_waiting > 0:
                data = self.serial.read(min(self.serial.in_waiting, buffer_size))
                return data
            return b''

        except Exception as e:
            print(f"Error reading: {e}")
            return None

    def trigger_broadcast(self, slave_address: int = 1):
        """
        Envía una petición Modbus para activar el broadcasting.

        El HP550 con bE=ON responde a peticiones Modbus con stream de broadcasting.

        Args:
            slave_address: Dirección del esclavo (default: 1)
        """
        if not self.is_connected():
            return False

        try:
            # Petición Modbus ASCII: Función 04, registro 0x0000, 1 registro
            # :010400000001FA\r\n
            query = f':{slave_address:02X}0400000001FA\r\n'

            # Limpiar buffers antes de enviar
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()

            # Enviar petición
            self.serial.write(query.encode('ascii'))
            self.serial.flush()

            return True

        except Exception as e:
            print(f"Error triggering broadcast: {e}")
            return False

    def read_and_parse(self, buffer_size: int = 512, trigger: bool = True, wait_time: float = 1.5):
        """
        Lee del buffer y parsea inmediatamente.

        Args:
            buffer_size: Tamaño máximo a leer
            trigger: Si True, envía petición Modbus antes de leer
            wait_time: Tiempo a esperar después de trigger (segundos)

        Returns:
            Diccionario con datos parseados o None
        """
        # Si trigger está activado, enviar petición primero
        if trigger:
            if not self.trigger_broadcast():
                return None
            # Esperar a que el HP550 responda
            time.sleep(wait_time)

        data = self.read_once(buffer_size)

        if data and len(data) > 0:
            return self.parser.parse_stream(data)

        return None

    def read_continuous(
        self,
        callback: Optional[Callable] = None,
        interval: float = 0.5,
        max_readings: Optional[int] = None
    ):
        """
        Lee continuamente del stream de broadcasting.

        Args:
            callback: Función a llamar con cada lectura parseada
            interval: Intervalo entre lecturas en segundos
            max_readings: Número máximo de lecturas (None = infinito)
        """
        if not self.is_connected():
            raise ConnectionError("Not connected")

        self._running = True
        readings_count = 0

        try:
            while self._running:
                # Leer y parsear
                reading = self.read_and_parse()

                if reading:
                    readings_count += 1

                    # Llamar callback si está definido
                    if callback:
                        callback(reading)

                    # Verificar límite de lecturas
                    if max_readings and readings_count >= max_readings:
                        break

                # Esperar intervalo
                time.sleep(interval)

        except KeyboardInterrupt:
            print("\nInterrupted by user")
        finally:
            self._running = False

    def stop(self):
        """Detiene la lectura continua."""
        self._running = False

    def get_connection_info(self):
        """
        Obtiene información de la conexión.

        Returns:
            Diccionario con parámetros de conexión
        """
        return {
            'port': self.port,
            'baudrate': self.baudrate,
            'parity': 'E' if self.parity == serial.PARITY_EVEN else 'N',
            'stopbits': self.stopbits,
            'bytesize': self.bytesize,
            'connected': self.is_connected()
        }

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
