from pydantic import BaseModel

class FaqModel(BaseModel, table=True):
    __tablename__ = "faq"
    title: str