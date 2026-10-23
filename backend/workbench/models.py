"""Validated, versioned public playbook contracts."""
from typing import Literal
import regex
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")

class Rule(Strict):
    id: str = Field(pattern=r"^[a-z][a-z0-9-]{1,79}$")
    category: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=3000)
    preferred_position: str = Field(min_length=1, max_length=3000)
    acceptable_alternatives: list[str] = Field(default_factory=list, max_length=20)
    unacceptable_conditions: list[str] = Field(min_length=1, max_length=20)
    severity: Literal["high", "medium", "low"]
    required: bool
    negotiation_guidance: str = Field(min_length=1, max_length=3000)
    fallback_language: str | None = Field(default=None, max_length=3000)
    # Each group must match at least one alternative. Patterns operate on category blocks.
    presence: list[str] = Field(min_length=1, max_length=20)
    acceptable_all: list[list[str]] = Field(min_length=1, max_length=20)
    unacceptable_any: list[str] = Field(default_factory=list, max_length=30)

    @field_validator("presence", "unacceptable_any")
    @classmethod
    def patterns(cls, items):
        for item in items:
            if not item or len(item) > 500:
                raise ValueError("Patterns must contain 1 to 500 characters")
            try:
                regex.compile(item)
            except regex.error as exc:
                raise ValueError("Invalid regular expression") from exc
        return items

    @field_validator("acceptable_all")
    @classmethod
    def groups(cls, groups):
        for group in groups:
            if not 1 <= len(group) <= 20:
                raise ValueError("Condition groups need 1 to 20 alternatives")
            cls.patterns(group)
        return groups

class Playbook(Strict):
    schema_version: Literal[1]
    name: str = Field(min_length=1, max_length=120)
    version: str = Field(min_length=1, max_length=40)
    description: str = Field(min_length=1, max_length=3000)
    rules: list[Rule] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def unique_ids(self):
        if len({r.id for r in self.rules}) != len(self.rules):
            raise ValueError("Rule IDs must be unique")
        return self

class YAMLInput(Strict):
    yaml: str = Field(min_length=1, max_length=200_000)

class ReviewInput(Strict):
    playbook_id: str

class Decision(Strict):
    status: Literal["accepted", "rejected", "unresolved"] | None = None
    notes: str | None = Field(default=None, max_length=10000)

    @model_validator(mode="after")
    def nonempty_patch(self):
        if not self.model_fields_set or any(getattr(self, key) is None for key in self.model_fields_set):
            raise ValueError("Supply status or notes; null values are not supported")
        return self

class AIInput(Strict):
    consent: bool
    model: str = Field(min_length=3, max_length=150, pattern=r"^[a-zA-Z0-9_.:/-]+$")
    provider: str = Field(min_length=2, max_length=100, pattern=r"^[a-zA-Z0-9_. /-]+$")
    max_output_tokens: int = Field(default=1024, ge=128, le=4096)
    max_cost_usd: float = Field(default=0.05, gt=0, le=1)

class VisualCheckInput(Strict):
    confirm_no_missing_text: Literal[True]
    original_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    extraction_revision: int = Field(ge=1)
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
