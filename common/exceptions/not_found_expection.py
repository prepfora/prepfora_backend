from common.exceptions.api_exception import APIException


class NotFoundException(APIException):
    status_code = 404
    message = "Not Found"

    def __init__(self, message: str = "Not Found") -> None:
        self.message = message
        super().__init__(message=self.message, status_code=self.status_code)