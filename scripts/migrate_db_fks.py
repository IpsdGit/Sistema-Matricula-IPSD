import argparse
import os
import shutil
import sqlite3

from config import DB_PATH


def table_exists(conn, table_name):
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (table_name,),
    ).fetchone()
    return bool(row)


def column_exists(conn, table_name, column_name):
    cols = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(col[1] == column_name for col in cols)


def add_docentes_centro_universitario(conn):
    if not table_exists(conn, 'docentes'):
        return
    if not column_exists(conn, 'docentes', 'centro_universitario_regional'):
        conn.execute(
            "ALTER TABLE docentes ADD COLUMN centro_universitario_regional TEXT NOT NULL DEFAULT ''"
        )


def migrate_matriculas(conn):
    if not table_exists(conn, 'matriculas'):
        return (0, 0)

    total = conn.execute('SELECT COUNT(*) FROM matriculas').fetchone()[0]

    conn.execute(
        '''
        CREATE TABLE matriculas_new (
            id INTEGER PRIMARY KEY,
            numero_empleado TEXT NOT NULL,
            id_capacitacion TEXT NOT NULL,
            horario_elegido TEXT NOT NULL,
            fecha_matricula DATETIME DEFAULT CURRENT_TIMESTAMP,
            aprobado INTEGER,
            fecha_aprobacion TEXT,
            FOREIGN KEY(numero_empleado) REFERENCES docentes(numero_empleado),
            FOREIGN KEY(id_capacitacion) REFERENCES capacitaciones(id)
        )
        '''
    )

    conn.execute(
        '''
        INSERT INTO matriculas_new (
            id, numero_empleado, id_capacitacion, horario_elegido,
            fecha_matricula, aprobado, fecha_aprobacion
        )
        SELECT
            m.id, m.numero_empleado, m.id_capacitacion, m.horario_elegido,
            m.fecha_matricula, m.aprobado, m.fecha_aprobacion
        FROM matriculas m
        JOIN docentes d ON d.numero_empleado = m.numero_empleado
        JOIN capacitaciones c ON c.id = m.id_capacitacion
        '''
    )

    insertados = conn.execute('SELECT COUNT(*) FROM matriculas_new').fetchone()[0]

    conn.execute('DROP TABLE matriculas')
    conn.execute('ALTER TABLE matriculas_new RENAME TO matriculas')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_matriculas_numero ON matriculas (numero_empleado)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_matriculas_capacitacion ON matriculas (id_capacitacion)')

    return (total, insertados)


def migrate_matricula_historial(conn):
    if not table_exists(conn, 'matricula_historial'):
        return (0, 0)

    total = conn.execute('SELECT COUNT(*) FROM matricula_historial').fetchone()[0]

    conn.execute(
        '''
        CREATE TABLE matricula_historial_new (
            id INTEGER PRIMARY KEY,
            matricula_id INTEGER,
            numero_empleado TEXT NOT NULL,
            id_capacitacion TEXT NOT NULL,
            nombre_curso TEXT NOT NULL,
            horario_elegido TEXT,
            estado_codigo TEXT NOT NULL,
            detalle TEXT,
            fecha_evento DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(matricula_id) REFERENCES matriculas(id),
            FOREIGN KEY(numero_empleado) REFERENCES docentes(numero_empleado),
            FOREIGN KEY(id_capacitacion) REFERENCES capacitaciones(id),
            FOREIGN KEY(estado_codigo) REFERENCES estado_matricula_catalogo(codigo)
        )
        '''
    )

    conn.execute(
        '''
        INSERT INTO matricula_historial_new (
            id, matricula_id, numero_empleado, id_capacitacion, nombre_curso,
            horario_elegido, estado_codigo, detalle, fecha_evento
        )
        SELECT
            mh.id, mh.matricula_id, mh.numero_empleado, mh.id_capacitacion, mh.nombre_curso,
            mh.horario_elegido, mh.estado_codigo, mh.detalle, mh.fecha_evento
        FROM matricula_historial mh
        JOIN docentes d ON d.numero_empleado = mh.numero_empleado
        JOIN capacitaciones c ON c.id = mh.id_capacitacion
        JOIN estado_matricula_catalogo e ON e.codigo = mh.estado_codigo
        LEFT JOIN matriculas m ON m.id = mh.matricula_id
        WHERE mh.matricula_id IS NULL OR m.id IS NOT NULL
        '''
    )

    insertados = conn.execute('SELECT COUNT(*) FROM matricula_historial_new').fetchone()[0]

    conn.execute('DROP TABLE matricula_historial')
    conn.execute('ALTER TABLE matricula_historial_new RENAME TO matricula_historial')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_historial_numero ON matricula_historial (numero_empleado)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_historial_matricula ON matricula_historial (matricula_id)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_historial_capacitacion ON matricula_historial (id_capacitacion)')

    return (total, insertados)


def migrate_registro_asistencia(conn):
    if not table_exists(conn, 'registro_asistencia'):
        return (0, 0)

    total = conn.execute('SELECT COUNT(*) FROM registro_asistencia').fetchone()[0]

    conn.execute(
        '''
        CREATE TABLE registro_asistencia_new (
            id_registro INTEGER PRIMARY KEY,
            id_sesion INTEGER NOT NULL,
            numero_empleado TEXT NOT NULL,
            fecha_marcado TEXT NOT NULL,
            hora_marcado TEXT NOT NULL,
            FOREIGN KEY(id_sesion) REFERENCES sesiones_curso(id_sesion),
            FOREIGN KEY(numero_empleado) REFERENCES docentes(numero_empleado)
        )
        '''
    )

    conn.execute(
        '''
        INSERT INTO registro_asistencia_new (
            id_registro, id_sesion, numero_empleado, fecha_marcado, hora_marcado
        )
        SELECT
            r.id_registro, r.id_sesion, r.numero_empleado, r.fecha_marcado, r.hora_marcado
        FROM registro_asistencia r
        JOIN docentes d ON d.numero_empleado = r.numero_empleado
        JOIN sesiones_curso s ON s.id_sesion = r.id_sesion
        '''
    )

    insertados = conn.execute('SELECT COUNT(*) FROM registro_asistencia_new').fetchone()[0]

    conn.execute('DROP TABLE registro_asistencia')
    conn.execute('ALTER TABLE registro_asistencia_new RENAME TO registro_asistencia')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_asistencia_numero ON registro_asistencia (numero_empleado)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_asistencia_sesion ON registro_asistencia (id_sesion)')

    return (total, insertados)


def parse_args():
    parser = argparse.ArgumentParser(description='Migracion de FKs y columnas en SQLite.')
    parser.add_argument('--backup', action='store_true', help='Crear copia .bak antes de migrar.')
    return parser.parse_args()


def main():
    args = parse_args()

    if args.backup:
        backup_path = DB_PATH + '.bak'
        shutil.copy2(DB_PATH, backup_path)
        print(f'Backup creado: {backup_path}')

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute('PRAGMA foreign_keys=OFF')
        add_docentes_centro_universitario(conn)

        total_m, ins_m = migrate_matriculas(conn)
        total_h, ins_h = migrate_matricula_historial(conn)
        total_a, ins_a = migrate_registro_asistencia(conn)

        conn.commit()
        conn.execute('PRAGMA foreign_keys=ON')

        print('Migracion completada')
        print(f'Matriculas: {ins_m}/{total_m} filas migradas')
        print(f'Historial: {ins_h}/{total_h} filas migradas')
        print(f'Asistencias: {ins_a}/{total_a} filas migradas')
    finally:
        conn.close()


if __name__ == '__main__':
    main()
