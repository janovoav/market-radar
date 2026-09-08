"""Envío de correo por SMTP (Gmail por defecto, cualquier proveedor sirve)."""
from __future__ import annotations

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send(subject: str, html_body: str) -> bool:
    user = os.environ.get("SMTP_USER")
    pwd = os.environ.get("SMTP_PASS")
    to = os.environ.get("EMAIL_TO", user)
    if not (user and pwd and to):
        print("   email: sin credenciales, se omite")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Market Radar <{user}>"
    msg["To"] = to
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "465"))
    try:
        with smtplib.SMTP_SSL(host, port, timeout=45) as srv:
            srv.login(user, pwd)
            srv.sendmail(user, [x.strip() for x in to.split(",")], msg.as_string())
        return True
    except smtplib.SMTPAuthenticationError:
        print("   email: autenticación rechazada. Con Gmail debes usar una "
              "'Contraseña de aplicación' de 16 caracteres, no tu clave normal.")
    except Exception as exc:  # noqa: BLE001
        print(f"   email error: {exc}")
    return False


def test_connection() -> tuple[bool, str]:
    user, pwd = os.environ.get("SMTP_USER"), os.environ.get("SMTP_PASS")
    if not (user and pwd):
        return False, "SMTP_USER o SMTP_PASS no están configurados"
    ok = send("Market Radar · prueba de conexión",
              "<h2>Correo configurado correctamente</h2>"
              "<p>Si ves esto, el canal de correo quedó listo.</p>")
    return (True, f"Correo de prueba enviado a {os.environ.get('EMAIL_TO', user)}") if ok \
        else (False, "No se pudo enviar. Revisa la contraseña de aplicación.")
