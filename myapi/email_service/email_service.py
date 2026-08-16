# import asyncio
# import sib_api_v3_sdk

# from backend.config import settings

# configuration = sib_api_v3_sdk.Configuration()
# configuration.api_key["api-key"] = settings.brevo_api_key.get_secret_value()

# api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
#     sib_api_v3_sdk.ApiClient(configuration)
# )


# async def send_email(
#     *,
#     recipient_email: str,
#     recipient_name: str,
#     subject: str,
#     html_content: str,
# ):
#     """
#     Send an HTML email using Brevo.
#     """

#     try:
#         email = sib_api_v3_sdk.SendSmtpEmail(
#             sender={
#                 "name": "Meeting Intelligence",
#                 "email": "batmanmishra23@gmail.com",
#             },
#             to=[
#                 {
#                     "email": recipient_email,
#                     "name": recipient_name,
#                 }
#             ],
#             subject=subject,
#             html_content=html_content,
#         )

#         response = await asyncio.to_thread(
#             api_instance.send_transac_email,
#             email,
#         )

#         print(f"Email sent successfully: {response}")

#         return response

#     except Exception as e:
#         print(f"Email sending failed: {e}")
#         raise



import sib_api_v3_sdk

from backend.config import settings

configuration = sib_api_v3_sdk.Configuration()
configuration.api_key["api-key"] = settings.brevo_api_key.get_secret_value()

api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
    sib_api_v3_sdk.ApiClient(configuration)
)


def send_email(
    *,
    recipient_email: str,
    recipient_name: str,
    subject: str,
    html_content: str,
):
    try:
        email = sib_api_v3_sdk.SendSmtpEmail(
            sender={
                "name": "Meeting Intelligence",
                "email": "batmanmishra23@gmail.com",  # later change it with your company domain
            },
            to=[
                {
                    "email": recipient_email,
                    "name": recipient_name,
                }
            ],
            subject=subject,
            html_content=html_content,
        )

        response = api_instance.send_transac_email(email)

        print(f"Email sent successfully to {recipient_email}")

        return response

    except Exception as e:
        print(f"Email sending failed: {e}")
        raise