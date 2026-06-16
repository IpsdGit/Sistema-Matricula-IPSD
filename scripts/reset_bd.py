import os
import sys
import psycopg2
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

# Importamos la función inicializar_bd del archivo setup_bd
from setup_bd import inicializar_bd, get_db_connection

# Cargar variables de entorno desde el archivo .env
load_dotenv()

def resetear_base_de_datos():
    """
    Esta función elimina absolutamente todas las tablas y datos de la base de datos
    y luego vuelve a crear la estructura limpia usando setup_bd.
    """
    print("⚠️  ADVERTENCIA DE PELIGRO ⚠️")
    print("Estás a punto de ELIMINAR TODA LA BASE DE DATOS (usuarios, cursos, matrículas, todo).")
    print("Esta acción NO se puede deshacer.")
    
    # 1. Pedir confirmación estricta por seguridad
    confirmacion = input("\nSi estás 100% seguro, escribe 'BORRAR TODO': ")
    
    if confirmacion != "BORRAR TODO":
        print("Cancelado. La base de datos no ha sido modificada.")
        sys.exit(0)
        
    print("\nProcesando limpieza total...")
    
    # 2. Conectarse a la base de datos
    conexion = get_db_connection()
    conexion.autocommit = True  # Necesario para borrar esquemas en algunos casos
    cursor = conexion.cursor()
    
    try:
        # 3. Eliminar el esquema público (donde viven todas las tablas) en cascada
        # Esto destruye todas las tablas y sus relaciones instantáneamente.
        cursor.execute("DROP SCHEMA public CASCADE;")
        
        # 4. Volver a crear el esquema público vacío
        cursor.execute("CREATE SCHEMA public;")
        
        # Restaurar permisos por defecto del esquema público (opcional pero buena práctica)
        cursor.execute("GRANT ALL ON SCHEMA public TO postgres;")
        cursor.execute("GRANT ALL ON SCHEMA public TO public;")
        
        print("✅ Esquema público borrado y recreado con éxito. La base de datos está vacía.")
        
    except psycopg2.Error as e:
        print(f"❌ Error al intentar borrar la base de datos: {e}")
        sys.exit(1)
    finally:
        cursor.close()
        conexion.close()
        
    # 5. Volver a crear las tablas y catálogos por defecto llamando a setup_bd
    print("Reconstruyendo las tablas base...")
    inicializar_bd()
    print("✅ ¡La base de datos ha sido reseteada y reconstruida exitosamente como nueva!")

if __name__ == '__main__':
    resetear_base_de_datos()
