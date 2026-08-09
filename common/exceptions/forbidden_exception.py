from common.exceptions.api_exception import APIException


class ForbiddenException(APIException):
    status_code = 403
    message = "Forbidden"