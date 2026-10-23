import os
import smtplib
from email.message import EmailMessage


def mail_configured():
    username = os.environ.get("MAIL_USERNAME", "").strip()
    password = os.environ.get("MAIL_APP_PASSWORD", "").strip()
    return bool(username and password and username != "CHANGE_ME" and password != "CHANGE_ME")


def send_password_reset(recipient, reset_url):
    if not mail_configured():
        raise RuntimeError("La configuración de correo no está completa")

    username = os.environ["MAIL_USERNAME"].strip()
    message = EmailMessage()
    message["Subject"] = "Recuperación de contraseña · ZYMA 360"
    message["From"] = f'{os.environ.get("MAIL_FROM_NAME", "ZYMA 360")} <{username}>'
    message["To"] = recipient
    message.set_content(
        "Recibimos una solicitud para restablecer tu contraseña.\n\n"
        f"Abre este enlace (válido durante 30 minutos):\n{reset_url}\n\n"
        "Si no realizaste esta solicitud, ignora este mensaje."
    )
    message.add_alternative(
        f"""
        <div style="font-family:Arial,sans-serif;color:#17251e;max-width:560px;margin:auto">
          <h2 style="color:#18794e">Recuperación de contraseña</h2>
          <p>Recibimos una solicitud para restablecer tu contraseña de Food Plant AI Copilot.</p>
          <p><a href="{reset_url}" style="display:inline-block;background:#18794e;color:white;padding:12px 18px;border-radius:8px;text-decoration:none;font-weight:bold">Crear nueva contraseña</a></p>
          <p style="color:#637069;font-size:13px">El enlace vence en 30 minutos y sólo puede utilizarse una vez.</p>
          <p style="color:#637069;font-size:13px">Si no realizaste esta solicitud, ignora este mensaje.</p>
        </div>
        """,
        subtype="html",
    )

    host = os.environ.get("MAIL_HOST", "smtp.gmail.com")
    port = int(os.environ.get("MAIL_PORT", "465"))
    password = os.environ["MAIL_APP_PASSWORD"].replace(" ", "")
    if os.environ.get("MAIL_USE_SSL", "true").lower() == "true":
        with smtplib.SMTP_SSL(host, port, timeout=15) as smtp:
            smtp.login(username, password)
            smtp.send_message(message)
    else:
        with smtplib.SMTP(host, port, timeout=15) as smtp:
            smtp.starttls()
            smtp.login(username, password)
            smtp.send_message(message)
