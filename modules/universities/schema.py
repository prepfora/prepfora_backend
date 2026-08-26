from pydantic import BaseModel


class UniversitySchema(BaseModel):
    name: str
    state: str
    city: str
    abbreviation: str
    website: str | None = None
    type: str | None = None


class UniversitiesListResponse(BaseModel):
    universities: list[UniversitySchema]
