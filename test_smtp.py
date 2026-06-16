import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

load_dotenv()

remitente = os.environ.get('EMAIL_USER')
password = os.environ.get('EMAIL_PASSWORD')

# Eliminar espacios de la contraseña de aplicación si los tiene
if password:
    password = password.replace(" ", "")

print(f"Probando conexión con:")
print(f"Usuario: {remitente}")
print(f"Contraseña (oculta): {'*' * len(password)}")

destinatario = remitente  # Enviarnos un correo a nosotros mismos para probar

msg = MIMEMultipart("alternative")
msg['Subject'] = "Prueba de Conexión - Sistema Matrícula IPSD"
msg['From'] = remitente
msg['To'] = destinatario

parte_html = MIMEText("<h2>Hola!</h2><p>Esta es una prueba de conexión con los servidores de Google.</p>", "html")
msg.attach(parte_html)

try:
    print("Conectando a smtp.gmail.com:587...")
    server = smtplib.SMTP('smtp.gmail.com', 587)
    
    print("Iniciando TLS...")
    server.starttls()
    
    print("Iniciando sesión...")
    server.login(remitente, password)
    
    print("Enviando correo...")
    server.sendmail(remitente, destinatario, msg.as_string())
    
    server.quit()
    print("¡Éxito! El correo de prueba se envió correctamente.")
except Exception as e:
    print(f"¡Error!: {e}")
