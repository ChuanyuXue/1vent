import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from config import DATE_FORMAT, SUMMARY_DIR, TIMEZONE
from comms import get_local_date


def setup_logging() -> None:
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )


def load_credentials() -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Load Gmail credentials from GitHub environment variables"""
    try:
        sender = os.environ.get("GMAIL_USER")
        password = os.environ.get("GMAIL_PASSWORD")
        recipient = os.environ.get("RECIPIENT_EMAIL")

        if not sender:
            logging.error("GMAIL_USER environment variable is not set")
        if not password:
            logging.error("GMAIL_PASSWORD environment variable is not set")
        if not recipient:
            logging.error("RECIPIENT_EMAIL environment variable is not set")

        if not sender or not password or not recipient:
            logging.error("Gmail credentials not found in environment variables")
            return None, None, None

        return sender, password, recipient
    except Exception as e:
        logging.error(f"Failed to load Gmail credentials: {e}")
        return None, None, None


def get_latest_summary() -> Optional[str]:
    """Get the most recent summary content"""
    try:
        summary_dir = Path(SUMMARY_DIR)
        today = get_local_date().strftime(DATE_FORMAT)
        summary_file = summary_dir / f"coding_summary_{today}.txt"

        # Add debug logging
        logging.info(f"Current working directory: {os.getcwd()}")
        logging.info(f"Looking for summary file at: {summary_file.absolute()}")

        if not summary_file.exists():
            logging.error(f"No summary file found for today: {summary_file}")
            return None

        with open(summary_file, "r") as f:
            return f.read()
    except Exception as e:
        logging.error(f"Error reading summary file: {e}")
        return None


def send_email(
    sender: str, password: str, recipient: str, subject: str, body: str
) -> bool:
    """Send email using Gmail SMTP"""
    try:
        # Create message
        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = recipient
        msg["Subject"] = (
            f"Coding Activity Summary - {get_local_date().strftime(DATE_FORMAT)}"
        )

        # Add body
        msg.attach(MIMEText(body, "plain"))

        # Connect to Gmail SMTP
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(sender, password)
            smtp.send_message(msg)

        logging.info(f"Email sent successfully to {recipient}")
        return True
    except Exception as e:
        logging.error(f"Failed to send email: {e}")
        return False


def main() -> None:
    """Main function to send coding summary via email"""
    setup_logging()

    # Load credentials
    sender, password, recipient = load_credentials()
    if not sender or not password or not recipient:
        logging.error("Gmail credentials not found in GitHub secrets")
        return

    # Get latest summary
    summary = get_latest_summary()
    if not summary:
        return

    # Create email content
    subject = (
        f"Daily Coding Activity Summary - {get_local_date().strftime(DATE_FORMAT)}"
    )
    body = f"""
Hello!

Here's your daily coding activity summary:

{summary}

Best regards,
1vents
https://github.com/ChuanyuXue/1vents
"""

    # Send email
    send_email(sender, password, recipient, subject, body)


if __name__ == "__main__":
    main()
