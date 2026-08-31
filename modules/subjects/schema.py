from pydantic import BaseModel


class SubjectFeatures(BaseModel):
    hasPassages: bool = False
    hasEquations: bool = False
    hasDiagrams: bool = False


class YearRange(BaseModel):
    min: int
    max: int


class SubjectSchema(BaseModel):
    name: str
    displayName: str
    code: str
    category: str
    aliases: list[str] = []
    questionCount: int = 0
    features: SubjectFeatures
    examTypes: list[str] = []
    yearRange: YearRange


class SubjectsListResponse(BaseModel):
    subjects: list[SubjectSchema]
