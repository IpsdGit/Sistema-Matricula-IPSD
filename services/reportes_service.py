import os
import json
import pandas as pd
from datetime import datetime
from database import get_db_connection
import psycopg2

def obtener_reporte_jerarquico(anio=None, calendario=None, periodo=None, centro_regional=None, facultad=None, admin_rol='admin', admin_direccion='IPSD'):
    try:
        conn = get_db_connection()
        
        # Filtros base
        params = []
        where_clauses = ["1=1"]
        
        if admin_rol != 'superadmin':
            where_clauses.append("ca.direccion_codigo = %s")
            params.append(admin_direccion)
            
        if anio:
            where_clauses.append("EXTRACT(YEAR FROM ef.fecha_inicio) = %s")
            params.append(anio)
            
        if calendario:
            where_clauses.append("ef.calendario_academico = %s")
            params.append(calendario)
            
        if periodo:
            where_clauses.append("ef.periodo = %s")
            params.append(periodo)
            
        where_sql = " AND ".join(where_clauses)
        
        # Filtros adicionales para matrícula (docentes)
        where_matricula = ""
        if centro_regional:
            where_matricula += " AND d.centro_universitario_regional = %s"
            params.append(centro_regional)
        if facultad:
            where_matricula += " AND d.facultad ILIKE %s"
            params.append(f'%{facultad}%')

        # Consulta unificada
        query = f'''
            SELECT 
                ca.id as catalogo_id, ca.nombre as accion_nombre, ca.tipo_accion,
                ef.id as edicion_id, ef.calendario_academico, ef.periodo, ef.fecha_inicio,
                m.id as matricula_id, m.aprobado,
                d.numero_empleado, d.nombre_completo, d.correo_institucional, d.centro_universitario_regional, d.facultad
            FROM catalogo_acciones ca
            JOIN ediciones_formativas ef ON ca.id = ef.catalogo_id
            LEFT JOIN matriculas m ON ef.id = m.edicion_id
            LEFT JOIN docentes d ON m.numero_empleado = d.numero_empleado
            WHERE {where_sql} {where_matricula}
            ORDER BY ca.nombre, ef.fecha_inicio DESC, d.nombre_completo
        '''
        
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor if hasattr(psycopg2, 'extras') else None) as cur:
            cur.execute(query, params)
            filas = cur.fetchall()

        # Procesar en jerarquía
        jerarquia = {}
        for row in filas:
            cat_id = row[0] if isinstance(row, tuple) else row['catalogo_id']
            if cat_id not in jerarquia:
                jerarquia[cat_id] = {
                    'catalogo_id': cat_id,
                    'accion_nombre': row[1] if isinstance(row, tuple) else row['accion_nombre'],
                    'tipo_accion': row[2] if isinstance(row, tuple) else row['tipo_accion'],
                    'total_matriculados': 0,
                    'total_aprobados': 0,
                    'ediciones': {}
                }
            
            ed_id = row[3] if isinstance(row, tuple) else row['edicion_id']
            if not ed_id:
                continue
                
            if ed_id not in jerarquia[cat_id]['ediciones']:
                jerarquia[cat_id]['ediciones'][ed_id] = {
                    'edicion_id': ed_id,
                    'calendario_academico': row[4] if isinstance(row, tuple) else row['calendario_academico'],
                    'periodo': row[5] if isinstance(row, tuple) else row['periodo'],
                    'fecha_inicio': row[6] if isinstance(row, tuple) else row['fecha_inicio'],
                    'matriculados': []
                }
                
            mat_id = row[7] if isinstance(row, tuple) else row['matricula_id']
            if mat_id:
                aprobado = row[8] if isinstance(row, tuple) else row['aprobado']
                mat_obj = {
                    'matricula_id': mat_id,
                    'aprobado': aprobado,
                    'numero_empleado': row[9] if isinstance(row, tuple) else row['numero_empleado'],
                    'nombre_completo': row[10] if isinstance(row, tuple) else row['nombre_completo'],
                    'correo_institucional': row[11] if isinstance(row, tuple) else row['correo_institucional'],
                    'centro_regional': row[12] if isinstance(row, tuple) else row['centro_universitario_regional'],
                    'facultad': row[13] if isinstance(row, tuple) else row['facultad'],
                }
                jerarquia[cat_id]['ediciones'][ed_id]['matriculados'].append(mat_obj)
                jerarquia[cat_id]['total_matriculados'] += 1
                if aprobado == 1:
                    jerarquia[cat_id]['total_aprobados'] += 1

        conn.close()
        return {'ok': True, 'jerarquia': list(jerarquia.values()), 'filas_planas': filas}
    except Exception as e:
        print(f"Error en obtener_reporte_jerarquico: {e}")
        return {'ok': False, 'jerarquia': [], 'filas_planas': []}


def generar_excel_y_registrar(filas_planas, titulo_reporte, admin_id, admin_username, parametros, formato="Excel"):
    try:
        # Convertir a Dataframe
        data = []
        for r in filas_planas:
            # Tolerancia para tuple o dict
            if isinstance(r, tuple):
                 data.append({
                    'ID Catálogo': r[0], 'Acción Formativa': r[1], 'Tipo': r[2],
                    'ID Edición': r[3], 'Calendario': r[4], 'Período': r[5], 'Fecha Inicio': r[6],
                    'Matrícula ID': r[7], 'Resultado': 'Aprobado' if r[8]==1 else 'Reprobado' if r[8]==0 else 'Abandonó' if r[8]==2 else 'Pendiente',
                    'Nº Empleado': r[9], 'Nombre Completo': r[10], 'Correo': r[11], 
                    'Centro Regional': r[12], 'Facultad': r[13]
                 })
            else:
                 data.append({
                    'ID Catálogo': r['catalogo_id'], 'Acción Formativa': r['accion_nombre'], 'Tipo': r['tipo_accion'],
                    'ID Edición': r['edicion_id'], 'Calendario': r['calendario_academico'], 'Período': r['periodo'], 'Fecha Inicio': r['fecha_inicio'],
                    'Matrícula ID': r['matricula_id'], 'Resultado': 'Aprobado' if r['aprobado']==1 else 'Reprobado' if r['aprobado']==0 else 'Abandonó' if r['aprobado']==2 else 'Pendiente',
                    'Nº Empleado': r['numero_empleado'], 'Nombre Completo': r['nombre_completo'], 'Correo': r['correo_institucional'], 
                    'Centro Regional': r['centro_universitario_regional'], 'Facultad': r['facultad']
                 })
                 
        df = pd.DataFrame(data)
        
        # Guardar en archivo
        os.makedirs('static/reportes', exist_ok=True)
        filename = f"reporte_{datetime.now().strftime('%Y%m%d%H%M%S')}_{admin_username}.xlsx"
        filepath = os.path.join('static/reportes', filename)
        df.to_excel(filepath, index=False)
        
        total_registros = len(data)

        # Registrar en BD
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO reportes_generados 
                (titulo_reporte, admin_id, parametros_extraccion, formato, total_registros_extraidos, ruta_archivo)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (titulo_reporte, admin_id, json.dumps(parametros), formato, total_registros, f"/static/reportes/{filename}"))
            conn.commit()
        conn.close()

        return {'ok': True, 'ruta_archivo': f"/static/reportes/{filename}", 'total': total_registros}
    except Exception as e:
        print(f"Error genero_excel: {e}")
        return {'ok': False, 'error': str(e)}

def obtener_historial_reportes():
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor if hasattr(psycopg2, 'extras') else None) as cur:
            cur.execute('''
                SELECT r.id, r.titulo_reporte, a.username as admin_username, r.fecha_generacion, 
                       r.parametros_extraccion, r.formato, r.total_registros_extraidos, r.ruta_archivo 
                FROM reportes_generados r
                LEFT JOIN admin_users a ON r.admin_id = a.id
                ORDER BY r.fecha_generacion DESC
            ''')
            registros = cur.fetchall()
        conn.close()
        
        # Convertir a lista de dicts
        res = []
        for row in registros:
            if isinstance(row, tuple):
                res.append({
                    'id': row[0], 'titulo_reporte': row[1], 'admin_username': row[2], 'fecha_generacion': row[3],
                    'parametros_extraccion': row[4], 'formato': row[5], 'total_registros_extraidos': row[6], 'ruta_archivo': row[7]
                })
            else:
                res.append(dict(row))
        return res
    except Exception as e:
         print(f"Error obtener historial: {e}")
         return []
