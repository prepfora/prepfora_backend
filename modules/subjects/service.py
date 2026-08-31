import httpx
from common.config import settings
from common.classes.return_type import ReturnType
from common.logger import logger
from common.exceptions.bad_request_exception import BadRequestException
from modules.subjects.schema import (
    SubjectSchema,
    SubjectsListResponse,
)

ALOC_SUBJECTS_URL = "https://dev.aloc.com.ng/api/v1/subjects"

DEFAULT_SUBJECTS = [
    {
        "name": "english",
        "displayName": "English Language",
        "code": "ENG",
        "category": "general",
        "aliases": ["english", "use-of-english", "english-language"],
        "questionCount": 1450,
        "features": {"hasPassages": True, "hasEquations": False, "hasDiagrams": False},
        "examTypes": ["waec", "jamb", "neco", "post_utme"],
        "yearRange": {"min": 1990, "max": 2024},
    },
    {
        "name": "mathematics",
        "displayName": "Mathematics",
        "code": "MTH",
        "category": "sciences",
        "aliases": ["math", "maths", "general-mathematics"],
        "questionCount": 1380,
        "features": {"hasPassages": False, "hasEquations": True, "hasDiagrams": True},
        "examTypes": ["waec", "jamb", "neco", "post_utme"],
        "yearRange": {"min": 1990, "max": 2024},
    },
    {
        "name": "physics",
        "displayName": "Physics",
        "code": "PHY",
        "category": "sciences",
        "aliases": ["phy", "physics"],
        "questionCount": 1120,
        "features": {"hasPassages": False, "hasEquations": True, "hasDiagrams": True},
        "examTypes": ["waec", "jamb", "neco", "post_utme"],
        "yearRange": {"min": 1990, "max": 2024},
    },
    {
        "name": "chemistry",
        "displayName": "Chemistry",
        "code": "CHM",
        "category": "sciences",
        "aliases": ["chem", "chemistry"],
        "questionCount": 1090,
        "features": {"hasPassages": False, "hasEquations": True, "hasDiagrams": True},
        "examTypes": ["waec", "jamb", "neco", "post_utme"],
        "yearRange": {"min": 1990, "max": 2024},
    },
    {
        "name": "biology",
        "displayName": "Biology",
        "code": "BIO",
        "category": "sciences",
        "aliases": ["bio", "biology"],
        "questionCount": 1150,
        "features": {"hasPassages": False, "hasEquations": False, "hasDiagrams": True},
        "examTypes": ["waec", "jamb", "neco", "post_utme"],
        "yearRange": {"min": 1990, "max": 2024},
    },
    {
        "name": "economics",
        "displayName": "Economics",
        "code": "ECO",
        "category": "commercial",
        "aliases": ["econ", "economics"],
        "questionCount": 980,
        "features": {"hasPassages": False, "hasEquations": True, "hasDiagrams": True},
        "examTypes": ["waec", "jamb", "neco", "post_utme"],
        "yearRange": {"min": 1990, "max": 2024},
    },
    {
        "name": "government",
        "displayName": "Government",
        "code": "GOV",
        "category": "arts",
        "aliases": ["gov", "government"],
        "questionCount": 940,
        "features": {"hasPassages": False, "hasEquations": False, "hasDiagrams": False},
        "examTypes": ["waec", "jamb", "neco", "post_utme"],
        "yearRange": {"min": 1990, "max": 2024},
    },
    {
        "name": "commerce",
        "displayName": "Commerce",
        "code": "COM",
        "category": "commercial",
        "aliases": ["commerce"],
        "questionCount": 870,
        "features": {"hasPassages": False, "hasEquations": False, "hasDiagrams": False},
        "examTypes": ["waec", "jamb", "neco", "post_utme"],
        "yearRange": {"min": 1990, "max": 2024},
    },
    {
        "name": "accounting",
        "displayName": "Financial Accounting",
        "code": "ACC",
        "category": "commercial",
        "aliases": ["financial-accounting", "accounting", "accounts"],
        "questionCount": 820,
        "features": {"hasPassages": False, "hasEquations": True, "hasDiagrams": False},
        "examTypes": ["waec", "jamb", "neco"],
        "yearRange": {"min": 1990, "max": 2024},
    },
    {
        "name": "crs",
        "displayName": "Christian Religious Studies",
        "code": "CRS",
        "category": "arts",
        "aliases": ["crk", "crs", "christian-religious-knowledge"],
        "questionCount": 790,
        "features": {"hasPassages": False, "hasEquations": False, "hasDiagrams": False},
        "examTypes": ["waec", "jamb", "neco"],
        "yearRange": {"min": 1990, "max": 2024},
    },
    {
        "name": "irs",
        "displayName": "Islamic Religious Studies",
        "code": "IRS",
        "category": "arts",
        "aliases": ["irk", "irs", "islamic-religious-knowledge"],
        "questionCount": 750,
        "features": {"hasPassages": False, "hasEquations": False, "hasDiagrams": False},
        "examTypes": ["waec", "jamb", "neco"],
        "yearRange": {"min": 1990, "max": 2024},
    },
    {
        "name": "geography",
        "displayName": "Geography",
        "code": "GEO",
        "category": "arts",
        "aliases": ["geo", "geography"],
        "questionCount": 810,
        "features": {"hasPassages": False, "hasEquations": True, "hasDiagrams": True},
        "examTypes": ["waec", "jamb", "neco"],
        "yearRange": {"min": 1990, "max": 2024},
    },
    {
        "name": "civiceducation",
        "displayName": "Civic Education",
        "code": "CIV",
        "category": "general",
        "aliases": ["civic", "civic-education"],
        "questionCount": 640,
        "features": {"hasPassages": False, "hasEquations": False, "hasDiagrams": False},
        "examTypes": ["waec", "neco"],
        "yearRange": {"min": 2010, "max": 2024},
    },
    {
        "name": "insurance",
        "displayName": "Insurance",
        "code": "INS",
        "category": "commercial",
        "aliases": ["insurance"],
        "questionCount": 420,
        "features": {"hasPassages": False, "hasEquations": False, "hasDiagrams": False},
        "examTypes": ["waec", "neco"],
        "yearRange": {"min": 2014, "max": 2024},
    },
    {
        "name": "currentaffairs",
        "displayName": "Current Affairs",
        "code": "CAF",
        "category": "general",
        "aliases": ["general-paper", "current-affairs"],
        "questionCount": 560,
        "features": {"hasPassages": False, "hasEquations": False, "hasDiagrams": False},
        "examTypes": ["post_utme"],
        "yearRange": {"min": 2005, "max": 2024},
    },
    {
        "name": "history",
        "displayName": "History",
        "code": "HIS",
        "category": "arts",
        "aliases": ["history"],
        "questionCount": 610,
        "features": {"hasPassages": False, "hasEquations": False, "hasDiagrams": False},
        "examTypes": ["waec", "jamb", "neco"],
        "yearRange": {"min": 1990, "max": 2024},
    },
    {
        "name": "literature",
        "displayName": "Literature in English",
        "code": "LIT",
        "category": "arts",
        "aliases": ["lit", "literature", "literature-in-english"],
        "questionCount": 890,
        "features": {"hasPassages": True, "hasEquations": False, "hasDiagrams": False},
        "examTypes": ["waec", "jamb", "neco"],
        "yearRange": {"min": 1990, "max": 2024},
    },
    {
        "name": "agricultural-science",
        "displayName": "Agricultural Science",
        "code": "AGR",
        "category": "sciences",
        "aliases": ["agric", "agric-science", "agricultural-science"],
        "questionCount": 920,
        "features": {"hasPassages": False, "hasEquations": False, "hasDiagrams": True},
        "examTypes": ["waec", "jamb", "neco"],
        "yearRange": {"min": 1990, "max": 2024},
    },
]


class SubjectsService:
    def __init__(self):
        self.access_token = settings.aloc_access_token
        self.headers = {
            "X-API-Key": self.access_token,
            "AccessToken": self.access_token,
            "Accept": "application/json",
        }

    async def _fetch_remote_subjects(self) -> list[dict] | None:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    ALOC_SUBJECTS_URL,
                    headers=self.headers,
                )
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
                        return data["data"]
        except Exception as e:
            logger.warning(f"Could not fetch remote subjects from ALOC: {str(e)}")
        return None

    async def get_subjects(
        self,
        category: str | None = None,
        search: str | None = None,
        exam_type: str | None = None,
    ) -> ReturnType[SubjectsListResponse]:
        try:
            logger.info("Fetching subjects catalog")
            raw_subjects = await self._fetch_remote_subjects()
            if not raw_subjects:
                raw_subjects = DEFAULT_SUBJECTS

            subjects = [SubjectSchema(**s) for s in raw_subjects]

            if category:
                cat_lower = category.strip().lower()
                subjects = [s for s in subjects if s.category.lower() == cat_lower]

            if search:
                term = search.strip().lower()
                subjects = [
                    s for s in subjects
                    if term in s.name.lower()
                    or term in s.displayName.lower()
                    or term in s.code.lower()
                    or any(term in alias.lower() for alias in s.aliases)
                ]

            if exam_type:
                et_lower = exam_type.strip().lower()
                subjects = [
                    s for s in subjects
                    if any(et_lower in et.lower() for et in s.examTypes)
                ]

            response_data = SubjectsListResponse(subjects=subjects)
            return ReturnType[SubjectsListResponse](
                success=True,
                message="Subjects fetched successfully",
                data=response_data,
            )
        except Exception as e:
            logger.error(f"Error fetching subjects: {str(e)}")
            raise BadRequestException(f"Failed to fetch subjects: {str(e)}")

    async def get_subject_by_name(self, name: str) -> ReturnType[SubjectSchema]:
        try:
            logger.info(f"Fetching subject details for '{name}'")
            target = name.strip().lower()
            raw_subjects = await self._fetch_remote_subjects()
            if not raw_subjects:
                raw_subjects = DEFAULT_SUBJECTS

            for s in raw_subjects:
                subject_obj = SubjectSchema(**s)
                if (
                    subject_obj.name.lower() == target
                    or subject_obj.code.lower() == target
                    or any(target == alias.lower() for alias in subject_obj.aliases)
                ):
                    return ReturnType[SubjectSchema](
                        success=True,
                        message="Subject fetched successfully",
                        data=subject_obj,
                    )

            raise BadRequestException(f"Subject '{name}' not found")
        except BadRequestException:
            raise
        except Exception as e:
            logger.error(f"Error fetching subject '{name}': {str(e)}")
            raise BadRequestException(f"Failed to fetch subject: {str(e)}")


def get_subjects_service() -> SubjectsService:
    return SubjectsService()
