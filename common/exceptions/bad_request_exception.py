from common.exceptions.api_exception import  APIException
class BadRequestException(APIException):
    status_code = 400
    message = "Bad Request"

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message=self.message, status_code=self.status_code)