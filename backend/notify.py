import os, smtplib, datetime
from email.message import EmailMessage

def send_email(to, subject, body):
    """Sends through SMTP if SMTP_HOST is set. Otherwise demo mode: print the email and save it to emails.log."""
    host = os.getenv("SMTP_HOST")
    if not host:
        text = f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] EMAIL demo\nTo: {to}\nSubject: {subject}\n{body}\n{'-' * 50}\n"
        print("\n" + text, flush=True)
        with open(os.path.join(os.path.dirname(__file__), "emails.log"), "a", encoding="utf-8") as f:
            f.write(text)
        return
    try:
        msg = EmailMessage()
        msg["From"] = os.getenv("SMTP_FROM", os.getenv("SMTP_USER", "noreply@training.local"))
        msg["To"] = to; msg["Subject"] = subject; msg.set_content(body)
        with smtplib.SMTP(host, int(os.getenv("SMTP_PORT", "587")), timeout=15) as s:
            s.starttls()
            if os.getenv("SMTP_USER"): s.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD", ""))
            s.send_message(msg)
    except Exception as e:
        print(f"[EMAIL failed] {to}: {e}", flush=True)