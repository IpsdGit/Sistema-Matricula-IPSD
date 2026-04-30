import sqlite3
import os

project_root = os.path.dirname(__file__)
db_path = os.path.join(project_root, 'matricula.db')

conexion = sqlite3.connect(db_path)
cursor = conexion.cursor()

cursor.execute('''
        CREATE TABLE IF NOT EXISTS plantillas_certificados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            direccion_codigo TEXT NOT NULL,
            nombre_plantilla TEXT NOT NULL,
            tipo_documento TEXT NOT NULL CHECK(tipo_documento IN ('DIPLOMA', 'CONSTANCIA')),
            ruta_firma_img TEXT NOT NULL,
            texto_certificado TEXT NOT NULL,
            firmante_nombre TEXT NOT NULL,
            firmante_cargo TEXT NOT NULL,
            activo INTEGER DEFAULT 1,
            FOREIGN KEY(direccion_codigo) REFERENCES direcciones(codigo)
        )
''')

try:
    cursor.execute('ALTER TABLE capacitaciones ADD COLUMN id_plantilla_certificado INTEGER REFERENCES plantillas_certificados(id)')
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e).lower():
        print("La columna id_plantilla_certificado ya existe.")
    else:
        raise e

conexion.commit()
conexion.close()
print("Migración completada exitosamente.")
