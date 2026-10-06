import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")


def send_email(to_email, subject, message):
    if not all([SMTP_HOST, SMTP_USER, SMTP_PASSWORD]):
        return False, "Email service is not configured."

    email = EmailMessage()
    email["Subject"] = subject
    email["From"] = SMTP_USER
    email["To"] = to_email
    email.set_content(message)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(email)

        return True, "Email sent."

    except Exception as e:
        return False, str(e)


def booking_created(to_email, restaurant, date, time, guests):
    return send_email(
        to_email,
        "DinePilot Booking Request",
        f"""
Your DinePilot booking request has been created.

Restaurant: {restaurant}
Date: {date}
Time: {time}
Guests: {guests}

Final confirmation depends on restaurant availability.
"""
    )


def booking_cancelled(to_email, restaurant, date, time):
    return send_email(
        to_email,
        "DinePilot Booking Cancelled",
        f"""
Your booking has been cancelled.

Restaurant: {restaurant}
Date: {date}
Time: {time}
"""
    )