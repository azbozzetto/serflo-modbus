"""
Script para exportar y visualizar datos capturados del HP550
"""

import sqlite3
import csv
import sys
import argparse
from datetime import datetime, timedelta


def export_to_csv(db_path: str, output_file: str, days: int = None):
    """
    Exporta datos de SQLite a CSV.

    Args:
        db_path: Ruta a la base de datos SQLite
        output_file: Archivo CSV de salida
        days: Número de días a exportar (None = todos)
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Construir query
    if days:
        cursor.execute('''
            SELECT timestamp_gmt, vl_cp, temperature_c, vc_cp
            FROM readings
            WHERE timestamp_gmt >= datetime('now', ?)
            ORDER BY timestamp_gmt
        ''', (f'-{days} days',))
    else:
        cursor.execute('''
            SELECT timestamp_gmt, vl_cp, temperature_c, vc_cp
            FROM readings
            ORDER BY timestamp_gmt
        ''')

    # Escribir CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Timestamp_GMT', 'VL_cP', 'Temperature_C', 'VC_cP'])

        count = 0
        for row in cursor:
            timestamp, vl, temp, vc = row
            vl_str = f"{vl:.2f}" if vl is not None else "N/A"
            temp_str = f"{temp:.1f}" if temp is not None else "N/A"
            vc_str = f"{vc:.2f}" if vc is not None else "N/A"

            writer.writerow([timestamp, vl_str, temp_str, vc_str])
            count += 1

    conn.close()

    print(f"Exported {count} records to {output_file}")


def show_stats(db_path: str):
    """
    Muestra estadísticas de los datos.

    Args:
        db_path: Ruta a la base de datos SQLite
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("\n" + "="*70)
    print("HP550 DATA STATISTICS")
    print("="*70)

    # Total de registros
    cursor.execute('SELECT COUNT(*) FROM readings')
    total = cursor.fetchone()[0]
    print(f"\nTotal records: {total}")

    if total == 0:
        print("\nNo data available yet.")
        conn.close()
        return

    # Primera y última lectura
    cursor.execute('SELECT MIN(timestamp_gmt), MAX(timestamp_gmt) FROM readings')
    first, last = cursor.fetchone()
    print(f"First reading: {first}")
    print(f"Last reading:  {last}")

    # Promedios
    cursor.execute('''
        SELECT
            AVG(vl_cp), MIN(vl_cp), MAX(vl_cp),
            AVG(temperature_c), MIN(temperature_c), MAX(temperature_c)
        FROM readings
        WHERE vl_cp IS NOT NULL OR temperature_c IS NOT NULL
    ''')
    avg_vl, min_vl, max_vl, avg_temp, min_temp, max_temp = cursor.fetchone()

    print(f"\nVL (cP):")
    if avg_vl:
        print(f"  Average: {avg_vl:.2f}")
        print(f"  Min:     {min_vl:.2f}")
        print(f"  Max:     {max_vl:.2f}")
    else:
        print("  No data")

    print(f"\nTemperature (°C):")
    if avg_temp:
        print(f"  Average: {avg_temp:.1f}")
        print(f"  Min:     {min_temp:.1f}")
        print(f"  Max:     {max_temp:.1f}")
    else:
        print("  No data")

    # Registros por día (últimos 7 días)
    print(f"\nRecords per day (last 7 days):")
    cursor.execute('''
        SELECT DATE(timestamp_gmt) as date, COUNT(*) as count
        FROM readings
        WHERE timestamp_gmt >= datetime('now', '-7 days')
        GROUP BY DATE(timestamp_gmt)
        ORDER BY date DESC
    ''')

    for row in cursor:
        date, count = row
        print(f"  {date}: {count} records")

    print("="*70 + "\n")

    conn.close()


def show_recent(db_path: str, limit: int = 10):
    """
    Muestra las lecturas más recientes.

    Args:
        db_path: Ruta a la base de datos SQLite
        limit: Número de registros a mostrar
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("\n" + "="*70)
    print(f"LAST {limit} READINGS")
    print("="*70)

    cursor.execute('''
        SELECT timestamp_gmt, vl_cp, temperature_c, vc_cp
        FROM readings
        ORDER BY id DESC
        LIMIT ?
    ''', (limit,))

    print(f"\n{'Timestamp (GMT)':<22} | {'VL (cP)':>10} | {'Temp (°C)':>10} | {'VC (cP)':>10}")
    print("-"*70)

    for row in cursor:
        timestamp, vl, temp, vc = row
        vl_str = f"{vl:>10.2f}" if vl is not None else f"{'N/A':>10}"
        temp_str = f"{temp:>10.1f}" if temp is not None else f"{'N/A':>10}"
        vc_str = f"{vc:>10.2f}" if vc is not None else f"{'N/A':>10}"

        print(f"{timestamp:<22} | {vl_str} | {temp_str} | {vc_str}")

    print("="*70 + "\n")

    conn.close()


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description='HP550 Data Export and Visualization Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python export_data.py --stats
  python export_data.py --recent 20
  python export_data.py --export output.csv
  python export_data.py --export output.csv --days 7
        """
    )

    parser.add_argument(
        '--db',
        default='data/hp550_data.db',
        help='Path to SQLite database (default: data/hp550_data.db)'
    )

    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show statistics'
    )

    parser.add_argument(
        '--recent',
        type=int,
        metavar='N',
        help='Show N most recent readings'
    )

    parser.add_argument(
        '--export',
        metavar='FILE',
        help='Export data to CSV file'
    )

    parser.add_argument(
        '--days',
        type=int,
        metavar='N',
        help='Export only last N days (use with --export)'
    )

    args = parser.parse_args()

    # Verificar que existe la base de datos
    import os
    if not os.path.exists(args.db):
        print(f"Error: Database not found: {args.db}")
        print("Run capture_24x7.py first to create the database.")
        sys.exit(1)

    # Ejecutar acción
    if args.stats:
        show_stats(args.db)

    if args.recent:
        show_recent(args.db, args.recent)

    if args.export:
        export_to_csv(args.db, args.export, args.days)

    # Si no se especificó ninguna acción, mostrar stats y recent por defecto
    if not (args.stats or args.recent or args.export):
        show_stats(args.db)
        show_recent(args.db, 10)


if __name__ == "__main__":
    main()
