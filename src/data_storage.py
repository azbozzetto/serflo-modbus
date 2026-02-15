"""
Sistema de almacenamiento de datos para HP550
Soporta SQLite y CSV con rotación automática
"""

import sqlite3
import csv
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional


class DataStorage:
    """
    Gestor de almacenamiento de datos del HP550.
    Soporta SQLite y/o CSV.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa el sistema de almacenamiento.

        Args:
            config: Diccionario de configuración
        """
        self.config = config['data_capture']
        self.storage_type = self.config.get('storage_type', 'sqlite')

        # Inicializar según tipo
        self.sqlite_conn = None
        self.current_csv_file = None
        self.current_csv_writer = None
        self.current_csv_date = None

        if self.storage_type in ['sqlite', 'both']:
            self._init_sqlite()

        if self.storage_type in ['csv', 'both']:
            self._init_csv()

    def _init_sqlite(self):
        """Inicializa base de datos SQLite."""
        db_path = self.config['sqlite']['database']

        # Crear directorio si no existe
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)

        # Conectar a base de datos
        self.sqlite_conn = sqlite3.connect(db_path, check_same_thread=False)

        # Crear tabla si no existe
        table_name = self.config['sqlite']['table_name']
        self.sqlite_conn.execute(f'''
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp_gmt TEXT NOT NULL,
                timestamp_local TEXT NOT NULL,
                vl_cp REAL,
                temperature_c REAL,
                vc_cp REAL,
                is_valid INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Crear índice en timestamp para búsquedas rápidas
        self.sqlite_conn.execute(f'''
            CREATE INDEX IF NOT EXISTS idx_timestamp
            ON {table_name}(timestamp_gmt)
        ''')

        self.sqlite_conn.commit()

    def _init_csv(self):
        """Inicializa sistema de CSV con rotación."""
        csv_dir = self.config['csv']['directory']

        # Crear directorio si no existe
        if not os.path.exists(csv_dir):
            os.makedirs(csv_dir)

    def _get_csv_file(self):
        """
        Obtiene el archivo CSV actual (con rotación automática por fecha).

        Returns:
            Tupla (file_object, csv_writer)
        """
        current_date = datetime.now().strftime('%Y%m%d')

        # Si es un nuevo día, cerrar archivo anterior y crear uno nuevo
        if self.current_csv_date != current_date:
            if self.current_csv_file:
                self.current_csv_file.close()

            # Crear nuevo archivo
            csv_dir = self.config['csv']['directory']
            filename_pattern = self.config['csv']['filename_pattern']
            filename = datetime.now().strftime(filename_pattern)
            filepath = os.path.join(csv_dir, filename)

            # Verificar si archivo ya existe
            file_exists = os.path.exists(filepath)

            # Abrir archivo
            self.current_csv_file = open(filepath, 'a', newline='', encoding='utf-8')
            self.current_csv_writer = csv.writer(self.current_csv_file)

            # Escribir encabezados si es nuevo
            if not file_exists:
                self.current_csv_writer.writerow([
                    'Timestamp_GMT',
                    'Timestamp_Local',
                    'VL_cP',
                    'Temperature_C',
                    'VC_cP'
                ])

            self.current_csv_date = current_date

        return self.current_csv_file, self.current_csv_writer

    def save_reading(
        self,
        vl: Optional[float] = None,
        temperature: Optional[float] = None,
        vc: Optional[float] = None
    ) -> bool:
        """
        Guarda una lectura en el sistema de almacenamiento.

        Args:
            vl: Viscosidad VL en cP
            temperature: Temperatura en °C
            vc: Viscosidad VC en cP

        Returns:
            True si se guardó exitosamente
        """
        timestamp_gmt = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        timestamp_local = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        success = True

        # Guardar en SQLite
        if self.storage_type in ['sqlite', 'both']:
            success &= self._save_to_sqlite(timestamp_gmt, timestamp_local, vl, temperature, vc)

        # Guardar en CSV
        if self.storage_type in ['csv', 'both']:
            success &= self._save_to_csv(timestamp_gmt, timestamp_local, vl, temperature, vc)

        return success

    def _save_to_sqlite(
        self,
        timestamp_gmt: str,
        timestamp_local: str,
        vl: Optional[float],
        temperature: Optional[float],
        vc: Optional[float]
    ) -> bool:
        """Guarda en SQLite."""
        try:
            table_name = self.config['sqlite']['table_name']
            self.sqlite_conn.execute(f'''
                INSERT INTO {table_name}
                (timestamp_gmt, timestamp_local, vl_cp, temperature_c, vc_cp)
                VALUES (?, ?, ?, ?, ?)
            ''', (timestamp_gmt, timestamp_local, vl, temperature, vc))
            self.sqlite_conn.commit()
            return True
        except Exception as e:
            print(f"Error saving to SQLite: {e}")
            return False

    def _save_to_csv(
        self,
        timestamp_gmt: str,
        timestamp_local: str,
        vl: Optional[float],
        temperature: Optional[float],
        vc: Optional[float]
    ) -> bool:
        """Guarda en CSV."""
        try:
            csvfile, writer = self._get_csv_file()

            vl_str = f"{vl:.2f}" if vl is not None else "N/A"
            temp_str = f"{temperature:.1f}" if temperature is not None else "N/A"
            vc_str = f"{vc:.2f}" if vc is not None else "N/A"

            writer.writerow([
                timestamp_gmt,
                timestamp_local,
                vl_str,
                temp_str,
                vc_str
            ])
            csvfile.flush()
            return True
        except Exception as e:
            print(f"Error saving to CSV: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de los datos almacenados.

        Returns:
            Diccionario con estadísticas
        """
        stats = {}

        if self.storage_type in ['sqlite', 'both'] and self.sqlite_conn:
            table_name = self.config['sqlite']['table_name']

            # Contar registros
            cursor = self.sqlite_conn.execute(f'SELECT COUNT(*) FROM {table_name}')
            stats['total_records'] = cursor.fetchone()[0]

            # Primera y última lectura
            cursor = self.sqlite_conn.execute(
                f'SELECT MIN(timestamp_gmt), MAX(timestamp_gmt) FROM {table_name}'
            )
            first, last = cursor.fetchone()
            stats['first_reading'] = first
            stats['last_reading'] = last

            # Promedios
            cursor = self.sqlite_conn.execute(f'''
                SELECT AVG(vl_cp), AVG(temperature_c), AVG(vc_cp)
                FROM {table_name}
                WHERE vl_cp IS NOT NULL OR temperature_c IS NOT NULL
            ''')
            avg_vl, avg_temp, avg_vc = cursor.fetchone()
            stats['avg_vl'] = avg_vl
            stats['avg_temperature'] = avg_temp
            stats['avg_vc'] = avg_vc

        return stats

    def cleanup_old_data(self, keep_days: int):
        """
        Elimina datos antiguos.

        Args:
            keep_days: Días de datos a mantener
        """
        if self.storage_type in ['sqlite', 'both'] and self.sqlite_conn:
            table_name = self.config['sqlite']['table_name']
            self.sqlite_conn.execute(f'''
                DELETE FROM {table_name}
                WHERE timestamp_gmt < datetime('now', '-{keep_days} days')
            ''')
            self.sqlite_conn.commit()

    def close(self):
        """Cierra conexiones y archivos."""
        if self.sqlite_conn:
            self.sqlite_conn.close()

        if self.current_csv_file:
            self.current_csv_file.close()

    def __del__(self):
        """Destructor."""
        self.close()
