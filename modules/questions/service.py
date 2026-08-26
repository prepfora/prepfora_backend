import httpx
from common.config import settings
from common.classes.return_type import ReturnType
from common.logger import logger
from common.exceptions.bad_request_exception import BadRequestException
from modules.questions.schema import (
    QuestionSingleResponse,
    QuestionMultipleResponse,
    QuestionItem,
)

ALOC_BASE_URL = "https://questions.aloc.com.ng/api/v2"


class QuestionsService:
    def __init__(self):
        self.access_token = settings.aloc_access_token
        self.headers = {
            "AccessToken": self.access_token,
            "Accept": "application/json",
        }

    async def get_random_question(
        self,
        subject: str = "english",
        type: str | None = None,
        year: str | int | None = None,
    ) -> ReturnType[QuestionSingleResponse]:
        try:
            logger.info(f"Fetching random question for subject={subject}")
            params = {"subject": subject}
            if type:
                params["type"] = type
            if year:
                params["year"] = str(year)

            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    f"{ALOC_BASE_URL}/q",
                    headers=self.headers,
                    params=params,
                )
                if response.status_code != 200:
                    logger.error(f"ALOC API Error: {response.text}")
                    raise BadRequestException("Failed to fetch question from ALOC API")

                res_data = response.json()
                single_resp = QuestionSingleResponse(**res_data)
                return ReturnType[QuestionSingleResponse](
                    success=True,
                    message="Question fetched successfully",
                    data=single_resp,
                )
        except BadRequestException:
            raise
        except Exception as e:
            logger.error(f"Error in get_random_question: {str(e)}")
            raise BadRequestException(f"Failed to fetch question: {str(e)}")

    async def get_multiple_questions(
        self,
        subject: str = "english",
        limit: int = 10,
        type: str | None = None,
        year: str | int | None = None,
    ) -> ReturnType[QuestionMultipleResponse]:
        try:
            logger.info(f"Fetching {limit} questions for subject={subject}")
            params = {"subject": subject}
            if type:
                params["type"] = type
            if year:
                params["year"] = str(year)

            endpoint = (
                f"{ALOC_BASE_URL}/q/{limit}"
                if limit and limit > 1
                else f"{ALOC_BASE_URL}/m"
            )

            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    endpoint,
                    headers=self.headers,
                    params=params,
                )
                if response.status_code != 200:
                    logger.error(f"ALOC API Error: {response.text}")
                    raise BadRequestException(
                        "Failed to fetch questions from ALOC API"
                    )

                res_data = response.json()
                data_field = res_data.get("data", [])
                items = []

                if isinstance(data_field, list):
                    items = [QuestionItem(**item) for item in data_field]
                elif isinstance(data_field, dict):
                    items = [QuestionItem(**data_field)]

                multi_resp = QuestionMultipleResponse(
                    subject=res_data.get("subject", subject),
                    status=res_data.get("status", 200),
                    data=items,
                )

                return ReturnType[QuestionMultipleResponse](
                    success=True,
                    message="Questions fetched successfully",
                    data=multi_resp,
                )
        except BadRequestException:
            raise
        except Exception as e:
            logger.error(f"Error in get_multiple_questions: {str(e)}")
            raise BadRequestException(f"Failed to fetch questions: {str(e)}")


def get_questions_service() -> QuestionsService:
    return QuestionsService()
