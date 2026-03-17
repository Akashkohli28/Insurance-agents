import os
import smtplib
import ssl
import logging
from email.message import EmailMessage
from twilio.rest import Client
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from logging_config import get_logger

load_dotenv()
logger = get_logger(__name__)

# LLM setup
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=os.getenv("GEMINI_API_KEY"))

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((smtplib.SMTPException, ConnectionError)),
    reraise=True
)
def send_email(to_email: str, subject: str, body: str):
    """Helper to send a real email using SMTP with retries."""
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "465"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    sender_email = os.getenv("SENDER_EMAIL", smtp_user)

    if not all([smtp_user, smtp_pass]):
        logger.warning(f"Skipping real email to {to_email} (Missing Credentials).")
        return False

    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = to_email

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as server:
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        logger.info(f"Real email sent to {to_email}.")
        return True
    except Exception as e:
        logger.error(f"Error sending email to {to_email}: {e}")
        raise # Reraise for retry decorator

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    reraise=True
)
def send_voice_call(to_number: str):
    """Helper to make a real voice call using Twilio with retries."""
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_PHONE_NUMBER")
    voice_url = os.getenv("TWILIO_VOICE_URL")

    if not all([account_sid, auth_token, voice_url]) or account_sid == "your_sid_here":
        logger.warning(f"Skipping real voice call to {to_number} (Missing Credentials).")
        return False

    try:
        client = Client(account_sid, auth_token)
        call = client.calls.create(
            url=voice_url,
            to=to_number,
            from_=(from_number or "+14155238886").replace("whatsapp:", "")
        )
        logger.info(f"Real voice call initiated to {to_number} (SID: {call.sid}).")
        return True
    except Exception as e:
        logger.error(f"Error initiating voice call to {to_number}: {e}")
        raise

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    reraise=True
)
def send_whatsapp(to_number: str, body: str):
    """Helper to send a real WhatsApp message using Twilio with retries."""
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_whatsapp_number = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

    if not all([account_sid, auth_token]) or account_sid == "your_sid_here":
        logger.warning(f"Skipping real WhatsApp message to {to_number} (Missing Credentials).")
        return False

    try:
        client = Client(account_sid, auth_token)
        message = client.messages.create(
            from_=from_whatsapp_number,
            body=body,
            to=f"whatsapp:{to_number}"
        )
        logger.info(f"Real WhatsApp sent to {to_number} (SID: {message.sid}).")
        return True
    except Exception as e:
        logger.error(f"Error sending WhatsApp to {to_number}: {e}")
        raise

def get_prompt(filename: str) -> str:
    """Helper to read a prompt from the prompts folder."""
    base_path = os.getenv("PROMPTS_DIR", os.path.join(os.path.dirname(__file__), "..", "prompts"))
    prompt_path = os.path.join(base_path, filename)
    try:
        with open(prompt_path, "r") as f:
            return f.read().strip()
    except Exception as e:
        logger.error(f"Error reading prompt file {filename}: {e}")
        return ""
