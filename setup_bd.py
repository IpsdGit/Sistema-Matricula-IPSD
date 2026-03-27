import sqlite3
import os

if os.path.exists('matricula.db'):
    os.remove('matricula.db')

def inicializar_bd():
    conexion = sqlite3.connect('matricula.db')
    cursor = conexion.cursor()

    # Agregamos las 3 columnas nuevas: anio, trimestre, mes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS capacitaciones (
            id TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            anio TEXT NOT NULL,
            trimestre TEXT NOT NULL,
            mes TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS horarios_curso (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_capacitacion TEXT NOT NULL,
            horario TEXT NOT NULL,
            FOREIGN KEY (id_capacitacion) REFERENCES capacitaciones (id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS matriculas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_empleado TEXT NOT NULL,
            id_capacitacion TEXT NOT NULL,
            horario_elegido TEXT NOT NULL,
            FOREIGN KEY (id_capacitacion) REFERENCES capacitaciones (id) ON DELETE CASCADE
        )
    ''')

    conexion.commit()
    conexion.close()
    print("¡Base de datos lista con soporte para control de periodos (Año, Trimestre, Mes)!")

if __name__ == '__main__':
    inicializar_bd()