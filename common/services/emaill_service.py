from common.logger import logger
from sqlalchemy.dialects.postgresql import Any
from ast import Dict
from common.exceptions.bad_request_exception import BadRequestException
import os
import resend

### Resend Payload

class ResendPayload[T]:
    to: str | list[str]
    subject: str
    html: str | None
    template: T | None


def send_email(payload: ResendPayload) -> None:
    if not payload.to:
        raise BadRequestException("reciever email missing")
    if not payload.html and not payload.template_id:
        raise BadRequestException("no template id or html provided")
    if payload.html:
        body: resend.Emails.SendParams = {
            "from": "Admin <support@prepfora@gmail.com>",
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
