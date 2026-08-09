class APIException(Exception):
    status_code = 500
    message = "Something went wrong"

    def __init__(self, message = None, status_code = 500, data = None, pagination = None):
        self.pagination = None
        if status_code is not None:
            self.status_code = status_code
        if message is not None:
            self.message = message
        self.data = data
