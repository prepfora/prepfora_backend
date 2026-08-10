from common.exceptions.api_exception import APIException

class InternalServerException(APIException):
    status_code = 500
    message = "Internal Server Error"