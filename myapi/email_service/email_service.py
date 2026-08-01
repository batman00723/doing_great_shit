import asyncio
import sib_api_v3_sdk
from backend.config import settings

configuration = sib_api_v3_sdk.Configuration()
configuration.api_key["api-key"] = settings.brevo_api_key.get_secret_value()

api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
    sib_api_v3_sdk.ApiClient(configuration)
)



async def send_email_report():
  
    try:
        email = sib_api_v3_sdk.SendSmtpEmail(
            sender={
                "name": "AI Receptionist Bot",
                "email": "batmanmishra23@gmail.com"
            },
            to=[{"email": "amanmishrarewa23@gmail.com"}],
            subject="Cancellation Alert Email",
            html_content=html
        )

        response= await asyncio.to_thread(api_instance.send_transac_email, email)
        print(f"Email sent successfully: {response}")
        return response

    except Exception as e:
        print(f"Error sending email: {e}")
        return None

