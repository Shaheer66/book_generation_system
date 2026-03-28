import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

def send_notification(to_email: str, subject: str, body: str):
    """
    Sends a production-grade email notification via SMTP.
    Requires SMTP_SERVER, SMTP_PORT, SMTP_USER, and SMTP_PASSWORD in .env.
    """
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASS")

    if not all([smtp_user, smtp_password, to_email]):
        logger.error("Email credentials or recipient missing. Skipping notification.")
        return False

    try:
        # Create the message
        msg = MIMEMultipart()
        msg['From'] = f"Book Engine <{smtp_user}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        # Connect and Send
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # Secure the connection
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
            
        logger.info(f"Notification sent successfully to {to_email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False