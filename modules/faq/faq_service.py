from typing import Any

from common.classes.return_type import ReturnType
from common.exceptions.bad_request_exception import BadRequestException


def get_faq(page: int, limit: int) -> ReturnType[Any]:
    if page < 1:
        raise BadRequestException(
            message="Page must be greater than 0",
        )

    return_type = ReturnType(
        success=True,
        data={"page": page, "limit": limit},
        message="Faqs returned",
        pagination=None,
    )
    return return_type