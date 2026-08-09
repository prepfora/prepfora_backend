from common.exceptions.api_exception import APIException

class UnauthorizedException(APIException):
    status_code = 401
    message = "Unauthorized"