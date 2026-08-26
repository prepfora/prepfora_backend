import json
from pathlib import Path
from common.classes.return_type import ReturnType
from common.logger import logger
from modules.universities.schema import UniversitiesListResponse, UniversitySchema

DATA_FILE = Path(__file__).parent / "universities.json"


class UniversitiesService:
    def __init__(self):
        self._data = None

    def _load_data(self) -> dict:
        if self._data is None:
            if DATA_FILE.exists():
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            else:
                self._data = {"universities": []}
        return self._data

    async def get_universities(
        self,
        name: str | None = None,
        state: str | None = None,
        search: str | None = None,
    ) -> ReturnType[UniversitiesListResponse]:
        try:
            logger.info("Fetching universities list with filters")
            raw_data = self._load_data()
            unis = raw_data.get("universities", [])

            if search:
                term = search.strip().lower()
                unis = [
                    u for u in unis
                    if term in u.get("name", "").lower()
                    or term in u.get("state", "").lower()
                    or term in u.get("abbreviation", "").lower()
                    or term in u.get("city", "").lower()
                ]

            if name:
                n_term = name.strip().lower()
                unis = [u for u in unis if n_term in u.get("name", "").lower()]

            if state:
                s_term = state.strip().lower()
                unis = [u for u in unis if s_term in u.get("state", "").lower()]

            response_data = UniversitiesListResponse(
                universities=[UniversitySchema(**u) for u in unis]
            )
            return ReturnType[UniversitiesListResponse](
                success=True,
                message="Universities fetched successfully",
                data=response_data,
            )
        except Exception as e:
            logger.error("Failed to fetch universities: " + str(e))
            raise Exception("Failed to fetch universities: " + str(e))


def get_universities_service() -> UniversitiesService:
    return UniversitiesService()
