import argparse
import os
import re
import sqlite3
import sys
import unicodedata
from datetime import datetime

from openpyxl import load_workbook

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import DB_PATH

DEFAULT_EXCEL_PATH = r"C:\Users\ipsd4\Desktop\Base de Prueba.xlsx"


def normalizar_texto(valor):
    return str(valor or '').strip()


def normalizar_correo(correo):
    return normalizar_texto(correo).lower()


def normalizar_cabecera(cabecera):
    texto = normalizar_texto(cabecera)
    texto = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('ascii')
    texto = re.sub(r'\s+', ' ', texto).strip().lower()
    return texto


def validar_numero_empleado(numero):
    return bool(re.match(r'^\d{4,12}$', numero))


def validar_correo(correo):
    return bool(re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', correo))


def asegurar_tabla_docentes(conn):
    cursor = conn.cursor()
    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS docentes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_empleado TEXT UNIQUE NOT NULL,
            nombre_completo TEXT NOT NULL,
            correo_institucional TEXT UNIQUE NOT NULL COLLATE NOCASE,
            activo INTEGER NOT NULL DEFAULT 1,
            fecha_sincronizacion DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        '''
    )
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_docentes_numero ON docentes (numero_empleado)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_docentes_correo ON docentes (correo_institucional)')
    conn.commit()


def resolver_columnas(headers):
    columnas_normalizadas = [normalizar_cabecera(c) for c in headers]

    alias_map = {
        'numero_empleado': {
            'numero de empleado',
            'numero empleado',
            'n de empleado',
            'no empleado',
            'num empleado',
        },
        'nombre_completo': {
            'nombre completo',
            'nombre',
        },
        'correo_institucional': {
            'correo institucional',
            'correo',
            'email institucional',
            'correo electronico',
            'correo electronico institucional',
        },
    }

    indices = {}
    for campo, alias in alias_map.items():
        for idx, nombre_col in enumerate(columnas_normalizadas):
            if nombre_col in alias:
                indices[campo] = idx
                break

    faltantes = [k for k in alias_map if k not in indices]
    if faltantes:
        raise ValueError(
            'No se encontraron columnas obligatorias en el Excel: ' + ', '.join(faltantes)
        )

    return indices


def sincronizar_docentes(excel_path, sheet_name=None, desactivar_ausentes=True):
    wb = load_workbook(excel_path, data_only=True, read_only=True)
    if sheet_name:
        if sheet_name not in wb.sheetnames:
            wb.close()
            raise ValueError(f'La hoja "{sheet_name}" no existe en el archivo Excel.')
        hoja = wb[sheet_name]
    else:
        hoja = wb.active

    if hoja is None:
        wb.close()
        raise ValueError('No se pudo determinar la hoja a procesar en el archivo Excel.')

    rows_iter = hoja.iter_rows(values_only=True)

    try:
        headers = next(rows_iter)
    except StopIteration as exc:
        wb.close()
        raise ValueError('El archivo Excel no contiene filas para procesar.') from exc

    indices = resolver_columnas(headers)

    total_filas = 0
    registros_validos = []
    errores_validacion = 0

    for row in rows_iter:
        total_filas += 1
        numero_empleado = normalizar_texto(row[indices['numero_empleado']] if indices['numero_empleado'] < len(row) else '')
        nombre_completo = normalizar_texto(row[indices['nombre_completo']] if indices['nombre_completo'] < len(row) else '')
        correo_institucional = normalizar_correo(
            row[indices['correo_institucional']] if indices['correo_institucional'] < len(row) else ''
        )

        if not numero_empleado or not nombre_completo or not correo_institucional:
            errores_validacion += 1
            continue

        if not validar_numero_empleado(numero_empleado) or not validar_correo(correo_institucional):
            errores_validacion += 1
            continue

        registros_validos.append((numero_empleado, nombre_completo, correo_institucional))

    wb.close()

    conn = sqlite3.connect(DB_PATH)
    try:
        asegurar_tabla_docentes(conn)
        cursor = conn.cursor()

        if desactivar_ausentes:
            cursor.execute('UPDATE docentes SET activo = 0')

        upserts_ok = 0
        conflictos = 0

        for numero_empleado, nombre_completo, correo_institucional in registros_validos:
            try:
                cursor.execute(
                    '''
                    INSERT INTO docentes (
                        numero_empleado, nombre_completo, correo_institucional, activo, fecha_sincronizacion
                    )
                    VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP)
                    ON CONFLICT(numero_empleado) DO UPDATE SET
                        nombre_completo = excluded.nombre_completo,
                        correo_institucional = excluded.correo_institucional,
                        activo = 1,
                        fecha_sincronizacion = CURRENT_TIMESTAMP
                    ''',
                    (numero_empleado, nombre_completo, correo_institucional),
                )
                upserts_ok += 1
            except sqlite3.IntegrityError:
                conflictos += 1

        conn.commit()
    finally:
        conn.close()

    return {
        'archivo': excel_path,
        'hoja': hoja.title,
        'db_path': DB_PATH,
        'fecha': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_filas': total_filas,
        'validos': len(registros_validos),
        'errores_validacion': errores_validacion,
        'upserts_ok': upserts_ok,
        'conflictos': conflictos,
        'desactivar_ausentes': desactivar_ausentes,
    }


def parse_args():
    parser = argparse.ArgumentParser(
        description='Sincroniza manualmente docentes desde un archivo Excel hacia SQLite.'
    )
    parser.add_argument(
        '--excel',
        default=DEFAULT_EXCEL_PATH,
        help='Ruta del archivo Excel con datos de docentes.',
    )
    parser.add_argument(
        '--sheet',
        default=None,
        help='Nombre de la hoja a procesar. Si se omite, usa la hoja activa.',
    )
    parser.add_argument(
        '--no-desactivar-ausentes',
        action='store_true',
        help='Si se usa, no desactiva docentes ausentes en el Excel.',
    )
    return parser.parse_args()


def main():
    args = parse_args()
    resultado = sincronizar_docentes(
        excel_path=args.excel,
        sheet_name=args.sheet,
        desactivar_ausentes=not args.no_desactivar_ausentes,
    )

    print('Sincronizacion completada')
    print(f"Fecha: {resultado['fecha']}")
    print(f"Archivo: {resultado['archivo']}")
    print(f"Hoja: {resultado['hoja']}")
    print(f"Base de datos: {resultado['db_path']}")
    print(f"Filas leidas: {resultado['total_filas']}")
    print(f"Registros validos: {resultado['validos']}")
    print(f"Registros sincronizados (insert/update): {resultado['upserts_ok']}")
    print(f"Errores de validacion: {resultado['errores_validacion']}")
    print(f"Conflictos por restricciones unicas: {resultado['conflictos']}")
    print(f"Docentes ausentes desactivados: {'si' if resultado['desactivar_ausentes'] else 'no'}")


if __name__ == '__main__':
    main()
