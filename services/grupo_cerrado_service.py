import openpyxl
from io import BytesIO
import time

_centros_cache = None
_centros_cache_time = 0

def obtener_centros_regionales(conn):
    """Retorna la lista de todos los centros regionales disponibles en la tabla de docentes."""
    cursor = conn.cursor()
    cursor.execute('''
        SELECT DISTINCT centro_universitario_regional 
        FROM docentes 
        WHERE activo = 1 
          AND centro_universitario_regional IS NOT NULL 
          AND centro_universitario_regional != ''
        ORDER BY centro_universitario_regional
    ''')
    return [row['centro_universitario_regional'] for row in cursor.fetchall()]

def obtener_docentes_por_centro(conn, centro):
    """Retorna la lista de docentes que pertenecen a un centro regional específico."""
    cursor = conn.cursor()
    cursor.execute('''
        SELECT numero_empleado, nombre_completo, centro_universitario_regional 
        FROM docentes 
        WHERE activo = 1 AND centro_universitario_regional = %s
        ORDER BY nombre_completo
    ''', (centro,))
    return [dict(row) for row in cursor.fetchall()]

def procesar_archivo_excel(file_stream):
    """
    Lee un archivo Excel usando openpyxl y extrae los valores de la primera columna.
    Retorna una lista limpia de strings.
    """
    try:
        wb = openpyxl.load_workbook(filename=BytesIO(file_stream.read()), data_only=True)
        sheet = wb.active
        
        numeros = []
        for row in sheet.iter_rows(min_col=1, max_col=1, values_only=True):
            val = row[0]
            if val is not None:
                # Limpiar cualquier espacio extra y convertir a string
                num_str = str(val).strip()
                if num_str:
                    numeros.append(num_str)
        return numeros
    except Exception as e:
        print(f"Error procesando Excel: {e}")
        return []

def validar_docentes(conn, lista_numeros_bruta):
    """
    Recibe una lista de strings (números de empleado), los busca en la BD y 
    retorna solo los docentes válidos como una lista de diccionarios.
    """
    if not lista_numeros_bruta:
        return []
        
    cursor = conn.cursor()
    # Usar ANY() para comparar con un array en Postgres
    cursor.execute('''
        SELECT numero_empleado, nombre_completo, centro_universitario_regional 
        FROM docentes 
        WHERE activo = 1 AND numero_empleado = ANY(%s)
    ''', (lista_numeros_bruta,))
    
    return [dict(row) for row in cursor.fetchall()]

def ejecutar_accion_grupo_cerrado(conn, edicion_id, accion, lista_docentes):
    """
    Ejecuta la matrícula automática o la invitación masiva.
    accion: 'automatica' o 'invitacion'
    lista_docentes: lista de números de empleado verificados
    """
    if not lista_docentes:
        return 0, 0 # insertados, ignorados
        
    cursor = conn.cursor()
    insertados = 0
    ignorados = 0
    
    for numero in lista_docentes:
        if accion == 'automatica':
            # Verificar si ya está matriculado
            cursor.execute('''
                SELECT 1 FROM matriculas 
                WHERE edicion_id = %s AND numero_empleado = %s
            ''', (edicion_id, numero))
            
            if not cursor.fetchone():
                cursor.execute('''
                    INSERT INTO matriculas (numero_empleado, edicion_id, aprobado)
                    VALUES (%s, %s, NULL)
                ''', (numero, edicion_id))
                
                # Crear registro en historial indicando que fue automática
                cursor.execute('SELECT id FROM matriculas WHERE edicion_id = %s AND numero_empleado = %s', (edicion_id, numero))
                matricula_id = cursor.fetchone()['id']
                     
                cursor.execute('''
                    INSERT INTO matricula_historial (
                        matricula_id, numero_empleado, edicion_id, nombre_accion,
                        estado_codigo, detalle
                    )
                    VALUES (%s, %s, %s, (SELECT nombre FROM catalogo_acciones WHERE id = (SELECT catalogo_id FROM ediciones_formativas WHERE id = %s)), %s, %s)
                ''', (
                    matricula_id, numero, edicion_id, edicion_id, 
                    'PENDIENTE', 'Matrícula asignada administrativamente (Grupo Cerrado)'
                ))
                
                insertados += 1
            else:
                ignorados += 1
                
        elif accion == 'invitacion':
            # Verificar si ya está invitado
            cursor.execute('''
                SELECT 1 FROM ediciones_invitaciones 
                WHERE edicion_id = %s AND numero_empleado = %s
            ''', (edicion_id, numero))
            
            if not cursor.fetchone():
                cursor.execute('''
                    INSERT INTO ediciones_invitaciones (edicion_id, numero_empleado)
                    VALUES (%s, %s)
                ''', (edicion_id, numero))
                insertados += 1
            else:
                ignorados += 1
                
    conn.commit()
    return insertados, ignorados
