import json


class Pagination:
    total: int
    page: int
    per_page: int
    def __init__(self, total: int, page: int, per_page: int):
        self.total = total
        self.page = page
        self.per_page = per_page


class ReturnType[T]:
    success: bool
    message: str
    data: T | None
    pagination: Pagination | None

    def __init__(self, success: bool, message: str, data: T = None, pagination: Pagination | None = None):
        self.success = success
        self.message = message
        self.data = data
        self.pagination = pagination

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

    def to_dict(self):
        return {
            "data": self.data,
            "message": self.message,
            "pagination": self.pagination,
            "success": self.success,
        }