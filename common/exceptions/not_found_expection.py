from common.exceptions.api_exception import APIException


class NotFoundException(APIException):
    status_code = 404
    message = "Not Found"