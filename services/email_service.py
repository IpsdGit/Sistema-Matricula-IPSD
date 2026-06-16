import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

load_dotenv()

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
        # Conexión al servidor SMTP de Gmail
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(remitente, password)
        server.sendmail(remitente, destinatario, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Error al enviar correo a {destinatario}: {e}")
        return False

def enviar_mensaje_docente(correo_docente, nombre_docente, asunto, mensaje):
    """
    Prepara la plantilla HTML y envía el correo al docente.
    """
    plantilla_html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #004b87;">Notificación Importante</h2>
        <p>Estimado/a <strong>{nombre_docente}</strong>,</p>
        <p>Tienes un nuevo mensaje del Sistema de Matrícula IPSD:</p>
        <div style="background-color: #f9f9f9; padding: 15px; border-left: 4px solid #004b87; margin-bottom: 20px;">
          <p style="margin: 0;">{mensaje.replace(chr(10), '<br>')}</p>
        </div>
        <p style="font-size: 0.9em; color: #777;">
          Puedes revisar este y otros mensajes ingresando a tu perfil en el <a href="https://portaldeaccionesformativasunah.duckdns.org/login">Portal de Acciones Formativas</a>.
        </p>
        <hr style="border: none; border-top: 1px solid #eee; margin-top: 30px;">
        <p style="font-size: 0.8em; color: #999; text-align: center;">
          Instituto de Profesionalización y Superación Docente (IPSD) - UNAH<br>
          Este es un mensaje automático, por favor no respondas a este correo.
        </p>
      </body>
    </html>
    """
    return enviar_correo(correo_docente, asunto, plantilla_html)
