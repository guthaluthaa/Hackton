from pydantic import BaseModel, field_validator
from typing import List

MAX_ITEM_LENGTH = 500
MAX_ITEMS = 20


class AnalysisResult(BaseModel):
    components: List[str]
    risks: List[str]
    recommendations: List[str]

    @field_validator("components", "risks", "recommendations", mode="before")
    @classmethod
    def sanitize_list(cls, v: List) -> List[str]:
        if not isinstance(v, list):
            raise ValueError("Must be a list")
        sanitized = [
            str(item)[:MAX_ITEM_LENGTH].strip()
            for item in v[:MAX_ITEMS]
            if item and str(item).strip()
        ]
        if not sanitized:
            raise ValueError("List must have at least one non-empty item")
        return sanitized
