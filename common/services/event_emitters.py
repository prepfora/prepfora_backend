from pydantic import BaseModel
from common.services.emaill_service import ResendPayload, send_email
from common.logger import logger
from pyee.asyncio import AsyncIOEventEmitter

# Create the Event Emitter instance
ee = AsyncIOEventEmitter()

# Register a listener (using a decorator, just like node)
class Send_Email_Payload(BaseModel):
    emails: list[str]
    message: str
    subject: str


@ee.on("send_emails")
async def handle_send_email(payload: Send_Email_Payload): 
   """
    Handle the sending of emails using a queue method so that everyone can get the emails 
    instead of sending it all at once
    loop through the emails one by one and send them
    if there is an error, log it and continue
   """
   logger.info("handle_send_emails called")
   for email in payload.emails:
    try:
        email_payload = ResendPayload(
            to=email,
            subject=payload.subject,
            html=f"<p>{payload.message}</p>"
        )
        result = send_email(email_payload)
        logger.info("Email sent successfully: " + str(result))
    except Exception as e:
        logger.error("Error sending email: " + str(e))
    finally:
        logger.info("one email has been sent")

