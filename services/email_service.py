import os
import smtplib
from datetime import date
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

load_dotenv()

# ── Tags disponibles para personalización ────────────────────────────────────
TAGS_DISPONIBLES = {
    '{{nombre_docente}}':     'Nombre completo del docente',
    '{{nombre_accion}}':      'Nombre de la acción formativa',
    '{{modalidad}}':          'Modalidad (Virtual / B-Learning / Presencial)',
    '{{duracion_horas}}':     'Duración en horas',
    '{{fecha_inicio}}':       'Fecha de inicio',
    '{{fecha_fin}}':          'Fecha de finalización (estimada)',
    '{{periodo}}':            'Período de ejecución',
    '{{enlace_acceso}}':      'Enlace directo al curso',
    '{{direccion}}':          'Nombre de la dirección / unidad académica',
}


def resolver_tags(texto, contexto: dict) -> str:
    """Reemplaza los tags {{...}} del mensaje con los valores del contexto."""
    for tag, valor in contexto.items():
        texto = texto.replace(tag, str(valor or ''))
    return texto


def enviar_correo(destinatario, asunto, cuerpo_html):
    """
    Envía un correo electrónico usando el servidor SMTP de Gmail.
    """
    remitente = os.environ.get('EMAIL_USER')
    password = os.environ.get('EMAIL_PASSWORD')

    if password:
        password = password.replace(' ', '')

    if not remitente or not password:
        print("Advertencia: Credenciales de correo no configuradas. El correo no se envió.")
        return False

    msg = MIMEMultipart("alternative")
    msg['Subject'] = asunto
    msg['From'] = remitente
    msg['To'] = destinatario

    parte_html = MIMEText(cuerpo_html, "html")
    msg.attach(parte_html)

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(remitente, password)
        server.sendmail(remitente, destinatario, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Error al enviar correo a {destinatario}: {e}")
        return False


def construir_plantilla_html(nombre_docente, asunto, cuerpo_mensaje):
    """
    Genera la plantilla HTML moderna con colores institucionales (UNAH azul).
    El cuerpo_mensaje ya tiene los tags resueltos.
    """
    año_actual = date.today().year
    # Convertir saltos de línea a <br> y envolver en párrafos si hay bloques
    cuerpo_html = cuerpo_mensaje.replace(chr(10), '<br>')

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{asunto}</title>
</head>
<body style="margin:0;padding:0;background-color:#f0f4f8;font-family:'Segoe UI',Arial,sans-serif;">

  <!-- Wrapper -->
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f0f4f8;padding:32px 0;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

          <!-- Header institucional -->
          <tr>
            <td style="background:linear-gradient(135deg,#003087 0%,#0052cc 60%,#0066ff 100%);border-radius:16px 16px 0 0;padding:32px 40px;text-align:center;">
              <p style="margin:0;color:rgba(255,255,255,0.75);font-size:11px;letter-spacing:2px;text-transform:uppercase;font-weight:600;">UNIVERSIDAD NACIONAL AUTÓNOMA DE HONDURAS</p>
              <h1 style="margin:8px 0 4px;color:#ffffff;font-size:22px;font-weight:700;letter-spacing:-0.3px;">Sistema de Acciones Formativas</h1>
              <p style="margin:0;color:rgba(255,255,255,0.8);font-size:13px;">Instituto de Profesionalización y Superación Docente</p>
              <div style="margin-top:16px;display:inline-block;background:rgba(255,255,255,0.15);border-radius:20px;padding:6px 18px;">
                <p style="margin:0;color:#ffffff;font-size:12px;font-weight:500;">✉ {asunto}</p>
              </div>
            </td>
          </tr>

          <!-- Body card -->
          <tr>
            <td style="background:#ffffff;padding:36px 40px;">

              <p style="margin:0 0 20px;color:#1e3a5f;font-size:16px;font-weight:600;">
                Estimado/a <span style="color:#003087;">{nombre_docente}</span>,
              </p>

              <!-- Mensaje principal -->
              <div style="background:#f8faff;border-left:4px solid #003087;border-radius:0 8px 8px 0;padding:20px 24px;margin-bottom:24px;">
                <p style="margin:0;color:#334155;font-size:14px;line-height:1.75;">{cuerpo_html}</p>
              </div>

              <hr style="border:none;border-top:1px solid #e2e8f0;margin:28px 0;">

              <!-- CTA -->
              <p style="margin:0 0 20px;color:#64748b;font-size:13px;text-align:center;">
                Puedes revisar este mensaje y más información ingresando al portal:
              </p>
              <div style="text-align:center;margin-bottom:8px;">
                <a href="https://portaldeaccionesformativasunah.duckdns.org"
                   style="display:inline-block;background:linear-gradient(135deg,#003087,#0052cc);color:#ffffff;font-size:14px;font-weight:600;text-decoration:none;padding:12px 32px;border-radius:50px;letter-spacing:0.3px;">
                  Ingresar al Portal Docente →
                </a>
              </div>

            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background:#1e3a5f;border-radius:0 0 16px 16px;padding:20px 40px;text-align:center;">
              <p style="margin:0 0 4px;color:rgba(255,255,255,0.9);font-size:12px;font-weight:600;letter-spacing:1px;text-transform:uppercase;">
                UNIVERSIDAD NACIONAL AUTÓNOMA DE HONDURAS
              </p>
              <p style="margin:0;color:rgba(255,255,255,0.5);font-size:11px;">
                © {año_actual} · Este es un mensaje automático, por favor no respondas a este correo.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>

</body>
</html>"""


def enviar_mensaje_docente(correo_docente, nombre_docente, asunto, mensaje, contexto_tags=None):
    """
    Resuelve tags, construye la plantilla HTML y envía el correo al docente.
    contexto_tags: dict con valores para reemplazar los {{tags}} del mensaje.
    """
    # Resolver tags si se proveen
    if contexto_tags:
        mensaje_resuelto = resolver_tags(mensaje, contexto_tags)
    else:
        # Sin contexto: reemplazar con valor vacío cualquier tag que quede
        mensaje_resuelto = mensaje

    plantilla_html = construir_plantilla_html(nombre_docente, asunto, mensaje_resuelto)
    return enviar_correo(correo_docente, asunto, plantilla_html)
