from common.exceptions.api_exception import APIException


class UnauthorizedException(APIException):
    status_code = 401
    message = "Unauthorized"

    def __init__(self, message: str = "Unauthorized") -> None:
        self.message = message
        super().__init__(message=self.message, status_code=self.status_code)