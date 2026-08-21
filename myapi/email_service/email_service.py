import logging
import httpx
from backend.config import settings

logger = logging.getLogger(__name__) 

async def send_email(
    *,
    recipient_email: str,
    recipient_name: str,
    subject: str,
    html_content: str,
):
    try:
        # 1. Grab the API key from your settings
        api_key = settings.brevo_api_key.get_secret_value() if settings.brevo_api_key else None
        if not api_key:
            raise ValueError("Brevo API key not configured.")

        # 2. Prepare the raw headers and JSON payload for the Brevo REST API
        url = "https://api.brevo.com/v3/smtp/email"
        headers = {
            "accept": "application/json",
            "api-key": api_key,
            "content-type": "application/json"
        }
        
        data = {
            "sender": {
                "name": "Meeting Intelligence",
                "email": "batmanmishra23@gmail.com",  # Later I will change this to my company domain
            },
            "to": [
                {
                    "email": recipient_email,
                    "name": recipient_name,
                }
            ],
            "subject": subject,
            "htmlContent": html_content,
        }

        # 3. Use httpx for true non-blocking async HTTP requests
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=data)
            
            # Brevo returns 201 (Created) or 202 (Accepted) on success
            if response.status_code not in [201, 202]:
                raise Exception(f"Brevo API Error: {response.text}")

        logging.info(f"Email sent successfully to {recipient_email}")
        return response.json()

    except Exception as e:
        logging.error(f"Email sending failed: {e}", exc_info=True)
        raise