#!/usr/bin/env python3
"""
migrate_db.py — Migración de base de datos HP550 a v1.2.0

Agrega las tablas partidas, eventos y muestras si no existen.
Es seguro ejecutar sobre una BD existente: usa CREATE TABLE IF NOT EXISTS
y no modifica datos ni tablas ya presentes.

Uso:
    python migrate_db.py
    python migrate_db.py --config config/config.yaml
    python migrate_db.py --db data/hp550_data.db
"""

import sqlite3
import argparse
import os
import sys

DEFAULT_CONFIG = 'config/config.yaml'


def load_db_path(config_path):
    try:
        import yaml
        with open(config_path) as f:
            cfg = yaml.safe_load(f)
        return cfg['data_capture']['sqlite']['database']
    except Exception as e:
        print(f"No se pudo leer config ({e}). Usando ruta por defecto: data/hp550_data.db")
        return 'data/hp550_data.db'


def migrate(db_path):
    if not os.path.exists(db_path):
        print(f"ERROR: No se encontró la base de datos en: {db_path}")
        sys.exit(1)

    print(f"Base de datos: {db_path}")
    conn = sqlite3.connect(db_path)

    # ── Tabla: readings (ya debería existir; se asegura por compatibilidad) ──
    conn.execute('''
        CREATE TABLE IF NOT EXISTS readings (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp_gmt   TEXT NOT NULL,
            timestamp_local TEXT NOT NULL,
            vl_cp           REAL,
            temperature_c   REAL,
            vc_cp           REAL,
            is_valid        INTEGER DEFAULT 1,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.execute('''
        CREATE INDEX IF NOT EXISTS idx_timestamp
        ON readings(timestamp_gmt)
    ''')

    # ── Tabla: partidas ───────────────────────────────────────────────────────
    conn.execute('''
        CREATE TABLE IF NOT EXISTS partidas (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha           TEXT NOT NULL,
            articulo        TEXT,
            numero_partida  INTEGER NOT NULL,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ── Tabla: eventos ────────────────────────────────────────────────────────
    conn.execute('''
        CREATE TABLE IF NOT EXISTS eventos (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            partida_id  INTEGER NOT NULL REFERENCES partidas(id),
            hora_evento TEXT NOT NULL,
            temperatura_c REAL,
            evento      TEXT NOT NULL,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ── Tabla: muestras ───────────────────────────────────────────────────────
    conn.execute('''
        CREATE TABLE IF NOT EXISTS muestras (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            partida_id           INTEGER NOT NULL REFERENCES partidas(id),
            hora_medicion        TEXT NOT NULL,
            tipo_medicion        TEXT NOT NULL CHECK(tipo_medicion IN ('lectura','laboratorio')),
            instrumento          TEXT,
            medicion_viscosidad  REAL NOT NULL,
            medicion_temperatura REAL NOT NULL,
            created_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()

    # ── Reporte ───────────────────────────────────────────────────────────────
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    rows = conn.execute("SELECT COUNT(*) FROM readings").fetchone()[0]
    conn.close()

    print(f"Tablas presentes: {', '.join(t[0] for t in tables)}")
    print(f"Lecturas existentes en readings: {rows:,}")
    print("Migración completada.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Migración de BD HP550 a v1.2.0')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--config', default=DEFAULT_CONFIG, help='Ruta al archivo de configuración')
    group.add_argument('--db', help='Ruta directa al archivo .db')
    args = parser.parse_args()

    db_path = args.db if args.db else load_db_path(args.config)
    migrate(db_path)
