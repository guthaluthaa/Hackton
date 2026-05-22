from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

MAX_ITEM_LENGTH = 500
MAX_ITEMS = 20
MIN_ITEMS = 1


class SeverityLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ScalabilityLevel(str, Enum):
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    HYBRID = "hybrid"
    NONE = "none"


class SecurityFinding(BaseModel):
    category: str = Field(..., min_length=3, max_length=100)
    description: str = Field(..., min_length=10, max_length=MAX_ITEM_LENGTH)
    severity: SeverityLevel
    affected_component: str = Field(..., min_length=2, max_length=200)

    @field_validator("category", mode="before")
    @classmethod
    def validate_category(cls, v: str) -> str:
        valid_categories = {
            "authentication", "authorization", "encryption", "data_exposure",
            "injection", "misconfiguration", "single_point_of_failure",
            "network_security", "api_security", "secrets_management",
            "logging_monitoring", "compliance", "access_control",
        }
        normalized = str(v).strip().lower().replace(" ", "_").replace("-", "_")
        if normalized not in valid_categories:
            closest = _find_closest_category(normalized, valid_categories)
            if closest:
                return closest
            raise ValueError(
                f"Invalid category '{v}'. Must be one of: {sorted(valid_categories)}"
            )
        return normalized


class ScalabilityAssessment(BaseModel):
    component: str = Field(..., min_length=2, max_length=200)
    current_pattern: ScalabilityLevel
    bottleneck_risk: str = Field(..., min_length=10, max_length=MAX_ITEM_LENGTH)
    recommendation: str = Field(..., min_length=10, max_length=MAX_ITEM_LENGTH)

    @field_validator("bottleneck_risk", "recommendation", mode="before")
    @classmethod
    def strip_and_validate(cls, v: str) -> str:
        cleaned = str(v).strip()
        if not cleaned:
            raise ValueError("Field cannot be empty")
        return cleaned


class AnalysisResult(BaseModel):
    components: List[str]
    risks: List[str]
    recommendations: List[str]
    security_findings: Optional[List[SecurityFinding]] = Field(default=None)
    scalability_assessments: Optional[List[ScalabilityAssessment]] = Field(default=None)
    architecture_type: Optional[str] = Field(default=None, max_length=100)
    overall_risk_score: Optional[float] = Field(default=None, ge=0.0, le=10.0)

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
        if len(sanitized) < MIN_ITEMS:
            raise ValueError("List must have at least one non-empty item")
        return sanitized

    @field_validator("security_findings", mode="before")
    @classmethod
    def validate_security_findings(cls, v) -> Optional[List]:
        if v is None:
            return None
        if not isinstance(v, list):
            raise ValueError("security_findings must be a list")
        return v[:MAX_ITEMS]

    @field_validator("scalability_assessments", mode="before")
    @classmethod
    def validate_scalability_assessments(cls, v) -> Optional[List]:
        if v is None:
            return None
        if not isinstance(v, list):
            raise ValueError("scalability_assessments must be a list")
        return v[:MAX_ITEMS]

    @model_validator(mode="after")
    def compute_risk_score(self) -> "AnalysisResult":
        if self.overall_risk_score is not None:
            return self
        if self.security_findings:
            severity_weights = {
                SeverityLevel.CRITICAL: 10.0,
                SeverityLevel.HIGH: 7.5,
                SeverityLevel.MEDIUM: 5.0,
                SeverityLevel.LOW: 2.5,
                SeverityLevel.INFO: 1.0,
            }
            total = sum(
                severity_weights.get(f.severity, 5.0)
                for f in self.security_findings
            )
            self.overall_risk_score = min(10.0, total / max(len(self.security_findings), 1))
        return self


def _find_closest_category(value: str, valid: set) -> Optional[str]:
    for valid_cat in valid:
        if value in valid_cat or valid_cat in value:
            return valid_cat
    return None
