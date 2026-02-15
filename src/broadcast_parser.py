"""
Parser para el stream de broadcasting del HP550 Hydramotion
Extrae valores de viscosidad y temperatura del formato de display
"""

import re
from typing import Dict, Optional, Any
from datetime import datetime


class HP550BroadcastParser:
    """
    Parser para datos de broadcasting del HP550.

    El HP550 con bE=ON transmite datos en formato de display:
    <WTVL ><WT  1204.5><WTcP>  -> VL = 1204.5 cP
    <WTVC ><WT     0.0><WTcP>  -> VC = 0.0 cP
    <WTt  ><WT    15.0><WT'C>  -> Temperatura = 15.0 °C
    """

    # Patrones para extraer datos
    PATTERN_VALUE = r'<WT\s*([\d.]+)>'
    PATTERN_UNIT = r'<WT([^>]+)>'
    PATTERN_TYPE = r'<WT([A-Z]+\s*)>'

    def __init__(self):
        """Inicializa el parser."""
        self.last_reading = {}
        self.reading_count = 0

    def parse_stream(self, data: bytes) -> Optional[Dict[str, Any]]:
        """
        Parsea un stream de datos del HP550.

        Args:
            data: Bytes recibidos del HP550

        Returns:
            Diccionario con los valores parseados o None si no se pudieron extraer
        """
        try:
            # Convertir a string
            text = data.decode('ascii', errors='ignore')

            # Extraer todos los valores numéricos
            values = re.findall(self.PATTERN_VALUE, text)

            # Inicializar lectura
            reading = {
                'timestamp': datetime.now().isoformat(),
                'raw_data': text,
            }

            # Buscar patrones específicos
            # VL (Viscosidad de Línea)
            vl_match = re.search(r'<WTVL\s*>.*?<WT\s*([\d.]+)>', text)
            if vl_match:
                reading['vl'] = float(vl_match.group(1))
                reading['vl_unit'] = 'cP'

            # VC (Viscosidad Corregida)
            vc_match = re.search(r'<WTVC\s*>.*?<WT\s*([\d.]+)>', text)
            if vc_match:
                reading['vc'] = float(vc_match.group(1))
                reading['vc_unit'] = 'cP'

            # VN (Viscosidad Normalizada)
            vn_match = re.search(r'<WTVN\s*>.*?<WT\s*([\d.]+)>', text)
            if vn_match:
                reading['vn'] = float(vn_match.group(1))
                reading['vn_unit'] = 'cP'

            # Temperatura
            temp_match = re.search(r'<WTt\s*>.*?<WT\s*([\d.]+)>', text)
            if temp_match:
                reading['temperature'] = float(temp_match.group(1))
                reading['temperature_unit'] = '°C'

            # Si encontramos al menos un valor, considerar válido
            if len(reading) > 2:  # Más que timestamp y raw_data
                self.reading_count += 1
                reading['reading_count'] = self.reading_count
                self.last_reading = reading
                return reading

            return None

        except Exception as e:
            print(f"Error parsing stream: {e}")
            return None

    def extract_all_values(self, text: str) -> Dict[str, Any]:
        """
        Extrae todos los valores encontrados en el texto.
        Método más general para debugging.

        Args:
            text: String a analizar

        Returns:
            Diccionario con todos los valores encontrados
        """
        result = {
            'timestamp': datetime.now().isoformat(),
            'values': [],
            'tags': []
        }

        # Extraer todos los valores numéricos
        values = re.findall(r'<WT\s*([\d.]+)>', text)
        result['values'] = [float(v) for v in values]

        # Extraer todos los tags
        tags = re.findall(r'<WT([A-Za-z\s\']+)>', text)
        result['tags'] = tags

        # Extraer pares tipo-valor
        pairs = re.findall(r'<WT([A-Z]+\s*)>.*?<WT\s*([\d.]+)>', text)
        result['pairs'] = pairs

        return result

    def format_reading(self, reading: Dict[str, Any]) -> str:
        """
        Formatea una lectura para impresión legible.

        Args:
            reading: Diccionario con los datos parseados

        Returns:
            String formateado
        """
        lines = [
            f"=== HP550 Broadcasting Reading #{reading.get('reading_count', 0)} ===",
            f"Time: {reading.get('timestamp', 'N/A')}",
            ""
        ]

        # Viscosidades
        if 'vl' in reading:
            lines.append(f"VL (Línea):      {reading['vl']:.1f} {reading.get('vl_unit', 'cP')}")

        if 'vc' in reading:
            lines.append(f"VC (Corregida):  {reading['vc']:.1f} {reading.get('vc_unit', 'cP')}")

        if 'vn' in reading:
            lines.append(f"VN (Normalizada): {reading['vn']:.1f} {reading.get('vn_unit', 'cP')}")

        # Temperatura
        if 'temperature' in reading:
            lines.append(f"Temperatura:     {reading['temperature']:.1f} {reading.get('temperature_unit', '°C')}")

        lines.append("=" * 60)

        return "\n".join(lines)

    def get_last_reading(self) -> Optional[Dict[str, Any]]:
        """
        Retorna la última lectura válida.

        Returns:
            Diccionario con la última lectura o None
        """
        return self.last_reading if self.last_reading else None

    def get_reading_count(self) -> int:
        """
        Retorna el número de lecturas procesadas.

        Returns:
            Contador de lecturas
        """
        return self.reading_count
