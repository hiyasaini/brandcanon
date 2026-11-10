"""Pydantic schemas for every structured model output. Model responses are never stored or shown unvalidated."""
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, ValidationError, field_validator

Category = Literal["Brand tone", "Brand personality", "Terminology", "Messaging", "Product specifications",
                   "Approved claims", "Prohibited claims", "Campaign instructions", "Visual identity",
                   "Accessibility requirements", "Other policies"]


class ExtractedRule(BaseModel):
    text: str = Field(min_length=3, max_length=600)
    category: Category = "Other policies"
    scope: str = "All content"


class ExtractedFact(BaseModel):
    product: str = Field(min_length=1, max_length=80)
    attribute: str = Field(min_length=1, max_length=80)
    value: float
    unit: str = Field(max_length=20)
    qualifier: str = ""
    text: str = Field(min_length=3, max_length=600)


class ExtractedTerm(BaseModel):
    term: str = Field(min_length=1, max_length=60)
    kind: Literal["prohibited", "preferred"]
    replacement: str = ""


class Extraction(BaseModel):
    rules: List[ExtractedRule] = []
    facts: List[ExtractedFact] = []
    terms: List[ExtractedTerm] = []


class CaseVerdict(BaseModel):
    id: int
    verdict: Literal["pass", "fail", "unclear"]
    reason: str = Field(min_length=1, max_length=400)


class CaseVerdicts(BaseModel):
    results: List[CaseVerdict]


class Clarification(BaseModel):
    rule: str = Field(min_length=5, max_length=600)


class AIFinding(BaseModel):
    quote: str = Field(min_length=2, max_length=300)
    category: Literal["Tone", "Messaging", "Unsupported claim"]
    severity: Literal["high", "medium", "low"]
    rule_code: Optional[str] = None
    message: str = Field(min_length=5, max_length=500)
    suggestion: str = Field(default="", max_length=400)

    @field_validator("rule_code")
    @classmethod
    def _code(cls, v):
        return v if v and v.startswith("R") else None


class AIFindings(BaseModel):
    findings: List[AIFinding] = []


def validate(model, data):
    """Return a validated model instance, or None if the data does not match the schema."""
    try:
        return model.model_validate(data)
    except ValidationError:
        return None


# ---------------------------------------------------------------- RuleProbe case generation
class GeneratedCase(BaseModel):
    aspect: str = Field(min_length=2, max_length=40)
    level: int = Field(ge=1, le=2)
    example: str = Field(min_length=5, max_length=280)


class GeneratedCases(BaseModel):
    baseline: str = Field(min_length=5, max_length=280)
    variants: List[GeneratedCase] = Field(min_length=2, max_length=8)


# ---------------------------------------------------------------- Content Auditor full rewrite
class Rewrite(BaseModel):
    text: str = Field(min_length=3, max_length=4000)
    changes: List[str] = Field(default=[], max_length=10)


# ---------------------------------------------------------------- Decision Memory summary
class PrecedentSummary(BaseModel):
    summary: str = Field(min_length=10, max_length=700)
    decision_ids: List[int] = Field(min_length=1)
