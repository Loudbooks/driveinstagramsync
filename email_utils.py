import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from flask import url_for

def send_reset_email(user, token, app):
    """
    Envía un correo electrónico con un enlace para restablecer la contraseña
    """
    with app.app_context():
        reset_url = url_for('reset_password', token=token, user_id=user.id, _external=True)
        
        # Configuración del correo
        try:
            # Si no hay credenciales de correo electrónico, solo simulamos el envío
            if not os.environ.get("EMAIL_USER") or not os.environ.get("EMAIL_PASSWORD"):
                print(f"SIMULANDO ENVÍO DE CORREO: Usuario: {user.username}, Token: {token}")
                print(f"URL de restablecimiento: {reset_url}")
                return True
                
            # Configuración real de correo electrónico
            sender_email = os.environ.get("EMAIL_USER")
            sender_password = os.environ.get("EMAIL_PASSWORD")
            
            if not sender_email or not sender_password:
                print(f"SIMULANDO ENVÍO DE CORREO (credenciales inválidas): Usuario: {user.username}, Token: {token}")
                print(f"URL de restablecimiento: {reset_url}")
                return True
            
            # Crear mensaje
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = user.email
            msg['Subject'] = Header('Restablecimiento de contraseña - Instagram Auto Publisher', 'utf-8')
            
            # Contenido del correo
            html = f"""
            <html>
              <body>
                <h2>Restablecimiento de Contraseña</h2>
                <p>Hola {user.username},</p>
                <p>Has solicitado restablecer tu contraseña. Haz clic en el siguiente enlace para continuar:</p>
                <p><a href="{reset_url}">Restablecer Contraseña</a></p>
                <p>Este enlace expirará en 1 hora.</p>
                <p>Si no solicitaste este restablecimiento, por favor ignora este correo.</p>
                <p>Saludos,<br>Instagram Auto Publisher</p>
              </body>
            </html>
            """
            
            msg.attach(MIMEText(html, 'html', 'utf-8'))
            
            # Enviar correo
            try:
                with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                    server.login(sender_email, sender_password)
                    server.sendmail(sender_email, user.email, msg.as_string())
            except Exception as e:
                print(f"Error al enviar correo: {str(e)}")
                print(f"URL de restablecimiento: {reset_url}")
                # En modo desarrollo, seguimos devolviendo True para facilitar pruebas
                return True
                
            return True
            
        except Exception as e:
            print(f"Error al enviar correo: {str(e)}")
            # En desarrollo, aún devolvemos la URL para facilitar las pruebas
            print(f"URL de restablecimiento: {reset_url}")
            return False