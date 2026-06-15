import io
import base64
import secrets

from database import get_db_connection


def generar_token_unico(codigo_direccion: str) -> str:
    """Genera un token seguro prefijado por el código de dirección."""
    codigo = (codigo_direccion or 'IPSD').upper().strip()
    hex_part = secrets.token_hex(8)  # 16 chars hex
    return f"{codigo}-{hex_part}"


def registrar_o_obtener_certificado(
    conn,
    matricula_id: int,
    numero_empleado: str,
    edicion_id: str,
    tipo_documento: str,
    codigo_direccion: str,
) -> str:
    """
    Busca si ya existe un certificado activo para esta matrícula.
    Si existe, devuelve el token. Si no, genera uno nuevo y lo registra.
    """
    with conn.cursor() as cur:
        cur.execute(
            '''
            SELECT token_validacion
            FROM certificados_emitidos
            WHERE matricula_id = %s 
              AND numero_empleado = %s 
              AND edicion_id = %s 
              AND activo = 1
            LIMIT 1
            ''',
            (matricula_id, numero_empleado, edicion_id),
        )
        fila = cur.fetchone()

    if fila:
        return fila['token_validacion']

    token = generar_token_unico(codigo_direccion)
    with conn.cursor() as cur:
        cur.execute(
            '''
            INSERT INTO certificados_emitidos
                (token_validacion, matricula_id, numero_empleado, edicion_id, tipo_documento)
            VALUES (%s, %s, %s, %s, %s)
            ''',
            (token, matricula_id, numero_empleado, edicion_id, tipo_documento),
        )
    conn.commit()
    return token


def generar_qr_base64(url_validacion: str) -> str:
    """
    Genera un QR en Base64 y retorna el Data URI completo (data:image/png;base64,...).
    border=2 es el mínimo recomendado para que wkhtmltopdf lo decodifique correctamente.
    """
    try:
        import qrcode

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=5,
            border=2,
        )
        qr.add_data(url_validacion)
        qr.make(fit=True)

        img = qr.make_image(fill_color='black', back_color='white')
        buffer = io.BytesIO()
        try:
            # Silenciamos la advertencia estricta del linter sobre 'format'
            img.save(buffer, format='PNG')  # type: ignore
        except TypeError:
            # Fallback para qrcode.image.pure.PyPNGImage que no acepta 'format'
            img.save(buffer)

        img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return f"data:image/png;base64,{img_str}"
    except Exception:
        return ''



def generar_qr_svg(url_validacion: str) -> str:
    """
    Genera un QR en SVG (path unico) y devuelve el string UTF-8.
    """
    try:
        import qrcode
        import qrcode.image.svg

        factory = qrcode.image.svg.SvgPathImage
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=4,
            border=1,
            image_factory=factory,
        )
        qr.add_data(url_validacion)
        qr.make(fit=True)
        img = qr.make_image()
        svg_str = img.to_string().decode('utf-8')

        if '<?xml' in svg_str:
            svg_str = svg_str.split('?>', 1)[-1].strip()

        if 'width=' not in svg_str:
            svg_str = svg_str.replace('<svg ', '<svg width="75" height="75" ', 1)
        else:
            import re
            svg_str = re.sub(r'width="[^"]+"', 'width="75"', svg_str)
            svg_str = re.sub(r'height="[^"]+"', 'height="75"', svg_str)

        return svg_str
    except Exception:
        return ''



def validar_certificado(conn, token: str) -> dict | None:
    """
    Valida un certificado por su token.
    Si es válido y activo, incrementa el contador de veces_validado
    y devuelve los datos completos del certificado, docente y curso.
    Returns None si no se encuentra o está revocado.
    """
    with conn.cursor() as cur:
        cur.execute(
            '''
            SELECT
                ce.id,
                ce.token_validacion,
                ce.matricula_id,
                ce.numero_empleado,
                ce.edicion_id,
                ce.fecha_emision,
                ce.tipo_documento,
                ce.veces_validado,
                ce.activo,
                d.nombre_completo,
                d.correo_institucional,
                d.centro_universitario_regional,
                ca.nombre AS nombre_curso,
                ca.modalidad
            FROM certificados_emitidos ce
            JOIN docentes d ON d.numero_empleado = ce.numero_empleado
            JOIN ediciones_formativas ef ON ef.id = ce.edicion_id
            JOIN catalogo_acciones ca ON ca.id = ef.catalogo_id
            WHERE ce.token_validacion = %s AND ce.activo = 1
            LIMIT 1
            ''',
            (token,),
        )
        fila = cur.fetchone()

    if not fila:
        return None

    # Incrementar el contador de escaneos
    with conn.cursor() as cur:
        cur.execute(
            'UPDATE certificados_emitidos SET veces_validado = veces_validado + 1 WHERE token_validacion = %s',
            (token,),
        )
    conn.commit()

    return dict(fila)
