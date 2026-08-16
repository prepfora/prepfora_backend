from dataclasses import dataclass
import os
import resend
from common.exceptions.bad_request_exception import BadRequestException
from common.logger import logger

### Resend Payload

@dataclass
class ResendPayload[T]:
    to: str | list[str]
    subject: str
    html: str | None = None
    template: T | None = None

RESEND_KEY = os.getenv("RESEND_KEY")

resend.api_key = RESEND_KEY


def send_email(payload: ResendPayload) -> None:
    if not payload.to:
        raise BadRequestException("reciever email missing")
    if not payload.html and not payload.template:
        raise BadRequestException("no template id or html provided")
    if payload.html:
        body: resend.Emails.SendParams = {
            "from": "Admin <support@prepfora.com>",
            "to": payload.to,
            "subject": payload.subject,
            "html": payload.html,
        }
        try:
            email = resend.Emails.send(body)
        except Exception as ex:
            logger.error(ex)
            raise BadRequestException("email not sent")
        logger.info(email)
        return email
    elif payload.template:
        body: resend.Emails.SendParams = {
            "from": "Admin <support@prepfora@gmail.com>",
            "to": payload.to,
            "subject": payload.subject,
            "template": payload.template
        }
        try:
            email = resend.Emails.send(body)
        except Exception as ex:
            logger.error(ex)
            raise BadRequestException("email not sent")
        logger.info(email)
        return email
