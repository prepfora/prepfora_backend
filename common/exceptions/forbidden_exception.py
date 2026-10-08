from common.exceptions.api_exception import APIException


class ForbiddenException(APIException):
    status_code = 403
    message = "Forbidden"

    def __init__(self, message: str = "Forbidden") -> None:
        self.message = message
        super().__init__(message=self.message, status_code=self.status_code)