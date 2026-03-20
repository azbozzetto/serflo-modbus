"""
HP550 Captura Continua 24/7 + Dashboard Web
Sistema robusto de captura de datos con reconexión automática
y visualización en tiempo real via navegador.
"""

import sys
import signal
import time
import sqlite3
import os
import threading
import logging
from pathlib import Path
from datetime import datetime

# Agregar directorio src al path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.broadcast_client import HP550BroadcastClient
from src.data_storage import DataStorage
from src.data_logger import HP550DataLogger
from src.utils import load_config, validate_config

from flask import Flask, jsonify, render_template, request, abort


# ─── Web Dashboard ───────────────────────────────────────────────────────────

def create_web_app(db_path, table_name):
    """Crea la aplicación Flask para el dashboard."""
    html_dir = os.path.join(os.path.dirname(__file__), 'html')
    app = Flask(__name__, template_folder=html_dir, static_folder=html_dir, static_url_path='/static')

    # Silenciar logs de Flask para no ensuciar la consola de captura
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.WARNING)

    def get_db():
        conn = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
        conn.row_factory = sqlite3.Row
        return conn

    def get_db_rw():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @app.route('/')
    def dashboard():
        return render_template('dashboard.html')

    @app.route('/api/partidas')
    def api_partidas_list():
        conn = get_db()
        try:
            rows = conn.execute(
                'SELECT id, fecha, articulo, numero_partida, created_at FROM partidas ORDER BY fecha DESC, id DESC'
            ).fetchall()
            return jsonify([dict(r) for r in rows])
        finally:
            conn.close()

    @app.route('/api/partidas/current')
    def api_partidas_current():
        conn = get_db()
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            row = conn.execute(
                'SELECT id, fecha, articulo, numero_partida, created_at FROM partidas WHERE fecha = ? ORDER BY id DESC LIMIT 1',
                (today,)
            ).fetchone()
            if not row:
                row = conn.execute(
                    'SELECT id, fecha, articulo, numero_partida, created_at FROM partidas ORDER BY fecha DESC, id DESC LIMIT 1'
                ).fetchone()
            if row:
                return jsonify(dict(row))
            return jsonify(None)
        finally:
            conn.close()

    @app.route('/api/partidas', methods=['POST'])
    def api_partidas_create():
        body = request.get_json(force=True) or {}
        fecha = body.get('fecha', '').strip()
        articulo = body.get('articulo', '').strip() or None
        numero_partida = body.get('numero_partida')
        if not fecha or numero_partida is None:
            return jsonify({'error': 'fecha y numero_partida son requeridos'}), 400
        conn = get_db_rw()
        try:
            cur = conn.execute(
                'INSERT INTO partidas (fecha, articulo, numero_partida) VALUES (?, ?, ?)',
                (fecha, articulo, int(numero_partida))
            )
            conn.commit()
            row = conn.execute('SELECT id, fecha, articulo, numero_partida, created_at FROM partidas WHERE id = ?', (cur.lastrowid,)).fetchone()
            return jsonify(dict(row)), 201
        finally:
            conn.close()

    @app.route('/api/partidas/<int:partida_id>/eventos')
    def api_eventos_list(partida_id):
        conn = get_db()
        try:
            rows = conn.execute(
                'SELECT id, partida_id, hora_evento, temperatura_c, evento, created_at FROM eventos WHERE partida_id = ? ORDER BY hora_evento ASC',
                (partida_id,)
            ).fetchall()
            return jsonify([dict(r) for r in rows])
        finally:
            conn.close()

    @app.route('/api/partidas/<int:partida_id>/eventos', methods=['POST'])
    def api_eventos_create(partida_id):
        body = request.get_json(force=True) or {}
        hora_evento = body.get('hora_evento', '').strip()
        evento = body.get('evento', '').strip()
        temperatura_c = body.get('temperatura_c')
        if not hora_evento or not evento:
            return jsonify({'error': 'hora_evento y evento son requeridos'}), 400
        conn = get_db_rw()
        try:
            cur = conn.execute(
                'INSERT INTO eventos (partida_id, hora_evento, temperatura_c, evento) VALUES (?, ?, ?, ?)',
                (partida_id, hora_evento, temperatura_c, evento)
            )
            conn.commit()
            row = conn.execute('SELECT id, partida_id, hora_evento, temperatura_c, evento, created_at FROM eventos WHERE id = ?', (cur.lastrowid,)).fetchone()
            return jsonify(dict(row)), 201
        finally:
            conn.close()

    @app.route('/api/partidas/<int:partida_id>/muestras')
    def api_muestras_list(partida_id):
        conn = get_db()
        try:
            rows = conn.execute(
                'SELECT id, partida_id, hora_medicion, tipo_medicion, instrumento, medicion_viscosidad, medicion_temperatura, created_at FROM muestras WHERE partida_id = ? ORDER BY hora_medicion ASC',
                (partida_id,)
            ).fetchall()
            return jsonify([dict(r) for r in rows])
        finally:
            conn.close()

    @app.route('/api/partidas/<int:partida_id>/muestras', methods=['POST'])
    def api_muestras_create(partida_id):
        body = request.get_json(force=True) or {}
        hora_medicion = body.get('hora_medicion', '').strip()
        tipo_medicion = body.get('tipo_medicion', '').strip()
        instrumento = body.get('instrumento') or None
        medicion_viscosidad = body.get('medicion_viscosidad')
        medicion_temperatura = body.get('medicion_temperatura')
        if not hora_medicion or tipo_medicion not in ('lectura', 'laboratorio') or medicion_viscosidad is None or medicion_temperatura is None:
            return jsonify({'error': 'Campos requeridos: hora_medicion, tipo_medicion, medicion_viscosidad, medicion_temperatura'}), 400
        conn = get_db_rw()
        try:
            cur = conn.execute(
                'INSERT INTO muestras (partida_id, hora_medicion, tipo_medicion, instrumento, medicion_viscosidad, medicion_temperatura) VALUES (?, ?, ?, ?, ?, ?)',
                (partida_id, hora_medicion, tipo_medicion, instrumento, float(medicion_viscosidad), float(medicion_temperatura))
            )
            conn.commit()
            row = conn.execute('SELECT id, partida_id, hora_medicion, tipo_medicion, instrumento, medicion_viscosidad, medicion_temperatura, created_at FROM muestras WHERE id = ?', (cur.lastrowid,)).fetchone()
            return jsonify(dict(row)), 201
        finally:
            conn.close()

    @app.route('/api/readings')
    def api_readings():
        hours = request.args.get('hours', 1, type=float)
        offset = request.args.get('offset', 0, type=float)
        limit = request.args.get('limit', 5000, type=int)
        partida_id = request.args.get('partida_id', None, type=int)
        date_str = request.args.get('date', None)   # 'YYYY-MM-DD' — vista día completo
        conn = get_db()
        try:
            if date_str:
                rows = conn.execute(f'''
                    SELECT timestamp_local, vl_cp, temperature_c, vc_cp
                    FROM {table_name}
                    WHERE date(timestamp_local) = ?
                      AND is_valid = 1
                    ORDER BY timestamp_local ASC
                    LIMIT ?
                ''', (date_str, limit)).fetchall()
            elif partida_id:
                partida = conn.execute('SELECT fecha FROM partidas WHERE id = ?', (partida_id,)).fetchone()
                if not partida:
                    return jsonify({'error': 'Partida no encontrada'}), 404
                rows = conn.execute(f'''
                    SELECT timestamp_local, vl_cp, temperature_c, vc_cp
                    FROM {table_name}
                    WHERE date(timestamp_local) = ?
                      AND is_valid = 1
                    ORDER BY timestamp_local ASC
                    LIMIT ?
                ''', (partida['fecha'], limit)).fetchall()
            elif offset > 0:
                rows = conn.execute(f'''
                    SELECT timestamp_local, vl_cp, temperature_c, vc_cp
                    FROM {table_name}
                    WHERE timestamp_gmt >= datetime('now', ? || ' hours')
                      AND timestamp_gmt <= datetime('now', ? || ' hours')
                      AND is_valid = 1
                    ORDER BY timestamp_gmt ASC
                    LIMIT ?
                ''', (str(-(hours + offset)), str(-offset), limit)).fetchall()
            else:
                rows = conn.execute(f'''
                    SELECT timestamp_local, vl_cp, temperature_c, vc_cp
                    FROM {table_name}
                    WHERE timestamp_gmt >= datetime('now', ? || ' hours')
                      AND is_valid = 1
                    ORDER BY timestamp_gmt ASC
                    LIMIT ?
                ''', (str(-hours), limit)).fetchall()
            data = {
                'timestamps': [],
                'vl': [],
                'temperature': [],
                'vc': [],
                'count': len(rows)
            }
            for row in rows:
                data['timestamps'].append(row['timestamp_local'])
                data['vl'].append(row['vl_cp'])
                data['temperature'].append(row['temperature_c'])
                data['vc'].append(row['vc_cp'])
            return jsonify(data)
        finally:
            conn.close()

    @app.route('/api/latest')
    def api_latest():
        conn = get_db()
        try:
            row = conn.execute(f'''
                SELECT timestamp_local, vl_cp, temperature_c, vc_cp
                FROM {table_name}
                WHERE is_valid = 1
                ORDER BY id DESC
                LIMIT 1
            ''').fetchone()
            if row:
                return jsonify({
                    'timestamp': row['timestamp_local'],
                    'vl': row['vl_cp'],
                    'temperature': row['temperature_c'],
                    'vc': row['vc_cp']
                })
            return jsonify({'error': 'No hay lecturas'}), 404
        finally:
            conn.close()

    @app.route('/api/stats')
    def api_stats():
        hours = request.args.get('hours', 24, type=float)
        offset = request.args.get('offset', 0, type=float)
        partida_id = request.args.get('partida_id', None, type=int)
        date_str = request.args.get('date', None)   # 'YYYY-MM-DD'
        conn = get_db()
        try:
            if date_str:
                row = conn.execute(f'''
                    SELECT COUNT(*) as total,
                        MIN(timestamp_local) as first_ts, MAX(timestamp_local) as last_ts,
                        AVG(vl_cp) as avg_vl, MIN(vl_cp) as min_vl, MAX(vl_cp) as max_vl,
                        AVG(temperature_c) as avg_temp, MIN(temperature_c) as min_temp, MAX(temperature_c) as max_temp
                    FROM {table_name}
                    WHERE date(timestamp_local) = ? AND is_valid = 1
                ''', (date_str,)).fetchone()
            elif partida_id:
                partida = conn.execute('SELECT fecha FROM partidas WHERE id = ?', (partida_id,)).fetchone()
                if not partida:
                    return jsonify({'error': 'Partida no encontrada'}), 404
                row = conn.execute(f'''
                    SELECT
                        COUNT(*) as total,
                        MIN(timestamp_local) as first_ts,
                        MAX(timestamp_local) as last_ts,
                        AVG(vl_cp) as avg_vl,
                        MIN(vl_cp) as min_vl,
                        MAX(vl_cp) as max_vl,
                        AVG(temperature_c) as avg_temp,
                        MIN(temperature_c) as min_temp,
                        MAX(temperature_c) as max_temp
                    FROM {table_name}
                    WHERE date(timestamp_local) = ?
                      AND is_valid = 1
                ''', (partida['fecha'],)).fetchone()
            elif offset > 0:
                row = conn.execute(f'''
                    SELECT
                        COUNT(*) as total,
                        MIN(timestamp_local) as first_ts,
                        MAX(timestamp_local) as last_ts,
                        AVG(vl_cp) as avg_vl,
                        MIN(vl_cp) as min_vl,
                        MAX(vl_cp) as max_vl,
                        AVG(temperature_c) as avg_temp,
                        MIN(temperature_c) as min_temp,
                        MAX(temperature_c) as max_temp
                    FROM {table_name}
                    WHERE timestamp_gmt >= datetime('now', ? || ' hours')
                      AND timestamp_gmt <= datetime('now', ? || ' hours')
                      AND is_valid = 1
                ''', (str(-(hours + offset)), str(-offset))).fetchone()
            else:
                row = conn.execute(f'''
                    SELECT
                        COUNT(*) as total,
                        MIN(timestamp_local) as first_ts,
                        MAX(timestamp_local) as last_ts,
                        AVG(vl_cp) as avg_vl,
                        MIN(vl_cp) as min_vl,
                        MAX(vl_cp) as max_vl,
                        AVG(temperature_c) as avg_temp,
                        MIN(temperature_c) as min_temp,
                        MAX(temperature_c) as max_temp
                    FROM {table_name}
                    WHERE timestamp_gmt >= datetime('now', ? || ' hours')
                      AND is_valid = 1
                ''', (str(-hours),)).fetchone()
            return jsonify({
                'total': row['total'],
                'period': {'from': row['first_ts'], 'to': row['last_ts']},
                'vl': {
                    'avg': round(row['avg_vl'], 2) if row['avg_vl'] else None,
                    'min': row['min_vl'],
                    'max': row['max_vl']
                },
                'temperature': {
                    'avg': round(row['avg_temp'], 1) if row['avg_temp'] else None,
                    'min': row['min_temp'],
                    'max': row['max_temp']
                }
            })
        finally:
            conn.close()

    return app


# ─── Captura 24/7 ────────────────────────────────────────────────────────────

class HP550Capture24x7:
    """
    Sistema de captura continua 24/7 para HP550.
    """

    def __init__(self, config_path: str = "config/config.yaml"):
        # Cargar configuración
        self.config = load_config(config_path)
        validate_config(self.config)

        # Verificar que captura esté habilitada
        if not self.config.get('data_capture', {}).get('enabled', False):
            raise ValueError("Data capture is not enabled in config.yaml")

        # Parámetros de captura
        self.capture_interval = self.config['data_capture']['interval']
        if self.capture_interval < 2:
            raise ValueError("Capture interval must be at least 2 seconds")

        # Reconexión
        self.reconnection_enabled = self.config['data_capture']['reconnection']['enabled']
        self.max_reconnect_attempts = self.config['data_capture']['reconnection']['max_attempts']
        self.retry_delay = self.config['data_capture']['reconnection']['retry_delay']

        # Inicializar componentes
        self.client = None
        self.storage = DataStorage(self.config)
        self.logger = HP550DataLogger(
            log_file=self.config['logging']['file'],
            log_level=self.config['logging']['level'],
            max_bytes=self.config['logging']['max_bytes'],
            backup_count=self.config['logging']['backup_count']
        )

        # Estado
        self.running = False
        self.total_readings = 0
        self.failed_readings = 0
        self.last_successful_reading = None

        # Variables para consolidar VL y temperatura
        self.last_vl = None
        self.last_temp = None
        self.last_vc = None

        # Web dashboard
        self.web_app = None
        self.web_thread = None
        self.web_port = self.config.get('web', {}).get('port', 5000)

    def _create_client(self) -> HP550BroadcastClient:
        """Crea una nueva instancia del cliente."""
        return HP550BroadcastClient(
            port=self.config['serial']['port'],
            baudrate=self.config['serial']['baudrate'],
            parity=self.config['serial']['parity'],
            stopbits=self.config['serial']['stopbits'],
            bytesize=self.config['serial']['bytesize'],
            timeout=self.config['serial']['timeout']
        )

    def _start_web_server(self):
        """Inicia el dashboard web en un hilo secundario."""
        db_path = self.config['data_capture']['sqlite']['database']
        table_name = self.config['data_capture']['sqlite']['table_name']
        self.web_app = create_web_app(db_path, table_name)

        self.web_thread = threading.Thread(
            target=lambda: self.web_app.run(
                host='0.0.0.0',
                port=self.web_port,
                debug=False,
                use_reloader=False
            ),
            daemon=True
        )
        self.web_thread.start()
        self.logger.log_info(f"Dashboard web: http://0.0.0.0:{self.web_port}")

    def connect(self) -> bool:
        self.logger.log_info("="*60)
        self.logger.log_info("HP550 CAPTURE 24/7 - Starting")
        self.logger.log_info("="*60)
        self.logger.log_info(f"Capture interval: {self.capture_interval} seconds")
        self.logger.log_info(f"Storage type: {self.config['data_capture']['storage_type']}")
        self.logger.log_info("="*60)

        try:
            self.client = self._create_client()

            if self.client.connect():
                self.logger.log_connection_event("connect", "Successfully connected to HP550")
                return True
            else:
                self.logger.log_error("Failed to connect to HP550")
                return False

        except Exception as e:
            self.logger.log_error("Connection error", e)
            return False

    def reconnect(self) -> bool:
        if not self.reconnection_enabled:
            self.logger.log_error("Reconnection disabled, exiting")
            return False

        attempts = 0
        max_attempts = self.max_reconnect_attempts

        while max_attempts == -1 or attempts < max_attempts:
            attempts += 1
            self.logger.log_warning(
                f"Reconnection attempt {attempts}/{max_attempts if max_attempts > 0 else 'unlimited'}"
            )

            try:
                if self.client:
                    try:
                        self.client.disconnect()
                    except:
                        pass

                time.sleep(self.retry_delay)

                if self.connect():
                    self.logger.log_info(f"Reconnected successfully after {attempts} attempts")
                    return True

            except Exception as e:
                self.logger.log_error(f"Reconnection attempt {attempts} failed", e)

        self.logger.log_error(f"Failed to reconnect after {attempts} attempts")
        return False

    def capture_reading(self) -> bool:
        try:
            reading = self.client.read_and_parse(
                buffer_size=512,
                trigger=True,
                wait_time=1.5
            )

            if not reading:
                self.failed_readings += 1
                return False

            updated = False
            if reading.get('vl') is not None:
                self.last_vl = reading['vl']
                updated = True

            if reading.get('temperature') is not None:
                self.last_temp = reading['temperature']
                updated = True

            if reading.get('vc') is not None:
                self.last_vc = reading['vc']
                updated = True

            if updated:
                success = self.storage.save_reading(
                    vl=self.last_vl,
                    temperature=self.last_temp,
                    vc=self.last_vc
                )

                if success:
                    self.total_readings += 1
                    self.last_successful_reading = datetime.now()

                    if self.total_readings % 10 == 0:
                        vl_str = f"{self.last_vl:.2f}" if self.last_vl else "N/A"
                        temp_str = f"{self.last_temp:.1f}" if self.last_temp else "N/A"
                        self.logger.log_info(
                            f"[{self.total_readings}] VL: {vl_str} cP, "
                            f"Temp: {temp_str} \u00b0C"
                        )

                    return True
                else:
                    self.failed_readings += 1
                    return False

            return True

        except Exception as e:
            self.logger.log_error("Error capturing reading", e)
            self.failed_readings += 1
            return False

    def run(self):
        """Ejecuta captura 24/7 + dashboard web."""
        self.running = True

        # Manejadores de señales
        def signal_handler(sig, frame):
            self.logger.log_info("Received termination signal")
            self.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Iniciar dashboard web
        self._start_web_server()

        # Conectar al HP550
        if not self.connect():
            self.logger.log_error("Failed to establish initial connection")
            if not self.reconnect():
                return

        self.logger.log_info("Starting continuous capture...")
        consecutive_failures = 0
        max_consecutive_failures = 10

        # Bucle principal
        while self.running:
            try:
                success = self.capture_reading()

                if success:
                    consecutive_failures = 0
                else:
                    consecutive_failures += 1

                if consecutive_failures >= max_consecutive_failures:
                    self.logger.log_error(
                        f"{consecutive_failures} consecutive failures, attempting reconnect"
                    )

                    if not self.reconnect():
                        self.logger.log_error("Reconnection failed, exiting")
                        break

                    consecutive_failures = 0

                time.sleep(self.capture_interval)

            except KeyboardInterrupt:
                self.logger.log_info("Interrupted by user")
                break

            except Exception as e:
                self.logger.log_error("Error in main loop", e)
                consecutive_failures += 1

                if consecutive_failures >= max_consecutive_failures:
                    if not self.reconnect():
                        break
                    consecutive_failures = 0

                time.sleep(self.capture_interval)

        self.stop()

    def stop(self):
        """Detiene la captura y cierra recursos."""
        self.running = False
        self.logger.log_info("="*60)
        self.logger.log_info("Stopping HP550 Capture 24/7")
        self.logger.log_info("="*60)
        self.logger.log_info(f"Total readings captured: {self.total_readings}")
        self.logger.log_info(f"Failed readings: {self.failed_readings}")

        if self.last_successful_reading:
            self.logger.log_info(f"Last successful reading: {self.last_successful_reading}")

        try:
            stats = self.storage.get_stats()
            if stats:
                self.logger.log_info(f"Database records: {stats.get('total_records', 'N/A')}")
                self.logger.log_info(f"First reading: {stats.get('first_reading', 'N/A')}")
                self.logger.log_info(f"Last reading: {stats.get('last_reading', 'N/A')}")
        except:
            pass

        self.logger.log_info("="*60)

        if self.client and self.client.is_connected():
            self.client.disconnect()

        self.storage.close()
        self.logger.close()

    def get_status(self) -> dict:
        return {
            'running': self.running,
            'total_readings': self.total_readings,
            'failed_readings': self.failed_readings,
            'last_successful_reading': self.last_successful_reading,
            'last_vl': self.last_vl,
            'last_temperature': self.last_temp,
            'connected': self.client.is_connected() if self.client else False
        }


def main():
    """Función principal."""
    import argparse

    parser = argparse.ArgumentParser(
        description='HP550 Continuous Data Capture 24/7 + Web Dashboard',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Configuration:
  Edit config/config.yaml to adjust:
  - data_capture.interval: Capture interval in seconds
  - data_capture.storage_type: "sqlite", "csv", or "both"
  - data_capture.reconnection: Auto-reconnection settings
  - web.port: Dashboard web port (default: 5000)

Example:
  python hp550_capture.py
  python hp550_capture.py --port 8080
  python hp550_capture.py --web-only

Press Ctrl+C to stop gracefully.
        """
    )

    parser.add_argument(
        '-c', '--config',
        default='config/config.yaml',
        help='Path to configuration file'
    )
    parser.add_argument(
        '-p', '--port',
        type=int,
        default=None,
        help='Web dashboard port (default: 5000)'
    )
    parser.add_argument(
        '--web-only',
        action='store_true',
        help='Solo iniciar dashboard web (sin captura, para revisar datos existentes)'
    )

    args = parser.parse_args()

    try:
        if args.web_only:
            # Modo solo dashboard: sin conexión al HP550
            config = load_config(args.config)
            db_path = config['data_capture']['sqlite']['database']
            table_name = config['data_capture']['sqlite']['table_name']
            port = args.port or config.get('web', {}).get('port', 5000)

            print(f"Base de datos: {db_path}")
            print(f"Dashboard: http://0.0.0.0:{port}")

            app = create_web_app(db_path, table_name)
            app.run(host='0.0.0.0', port=port, debug=False)
        else:
            # Modo completo: captura + dashboard
            capture = HP550Capture24x7(config_path=args.config)
            if args.port:
                capture.web_port = args.port
            capture.run()

    except ValueError as e:
        print(f"Configuration error: {e}")
        sys.exit(1)

    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
