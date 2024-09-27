import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

smtp_server = "smtp.mail.me.com"
port = 587
sender_email = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@buyinggrouppro.com')
login_email = os.environ.get('EMAIL_HOST_USER', 'jerredrogero@icloud.com')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')

print(f"Sender Email: {sender_email}")
print(f"Login Email: {login_email}")
print(f"Password set: {'Yes' if EMAIL_HOST_PASSWORD else 'No'}")

try:
    print(f"Connecting to {smtp_server}:{port}...")
    server = smtplib.SMTP(smtp_server, port)
    print("Starting TLS...")
    server.starttls()
    print(f"Attempting login with {login_email}...")
    server.login(login_email, EMAIL_HOST_PASSWORD)
    print("SMTP connection and login successful")

    message = MIMEMultipart()
    message['From'] = sender_email
    message['To'] = "djrdog578@gmail.com"  # Replace with your test email
    message['Subject'] = "Test Email from Django App"

    body = "This is a test email sent from your Django application using iCloud custom domain."
    message.attach(MIMEText(body, 'plain'))

    print("Sending email...")
    server.send_message(message)
    print("Test email sent successfully")

except Exception as e:
    print(f"An error occurred: {e}")

finally:
    if 'server' in locals():
        server.quit()