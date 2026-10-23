"""Editable review preferences. Pattern logic remains in advanced YAML."""
import hashlib
import json
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import Field, model_validator
import yaml

from . import store
from .models import Strict

router = APIRouter()
RULE_FIELDS = ("id", "category", "description", "severity", "required", "preferred_position", "negotiation_guidance", "fallback_language")


class RuleSettings(Strict):
    id: str
    severity: Literal["high", "medium", "low"] | None = None
    required: bool | None = None
    preferred_position: str | None = Field(default=None, min_length=1, max_length=3000)
    negotiation_guidance: str | None = Field(default=None, min_length=1, max_length=3000)
    fallback_language: str | None = Field(default=None, max_length=3000)

    @model_validator(mode="after")
    def no_null_required_fields(self):
        if any(getattr(self, key) is None for key in self.model_fields_set - {"fallback_language"}):
            raise ValueError("Only fallback language can be cleared")
        return self


class SettingsPatch(Strict):
    revision: str = Field(pattern=r"^[0-9a-f]{64}$")
    name: str | None = Field(default=None, min_length=1, max_length=120)
    version: str | None = Field(default=None, min_length=1, max_length=40)
    description: str | None = Field(default=None, min_length=1, max_length=3000)
    rules: list[RuleSettings] | None = Field(default=None, min_length=1, max_length=100)

    @model_validator(mode="after")
    def valid_patch(self):
        if self.model_fields_set == {"revision"} or any(getattr(self, key) is None for key in self.model_fields_set):
            raise ValueError("Supply a nonempty settings change")
        if self.rules and len({r.id for r in self.rules}) != len(self.rules):
            raise ValueError("Duplicate rule IDs")
        return self


def revision(text):
    return hashlib.sha256(text.encode()).hexdigest()


def view(record):
    from .main import parse_playbook
    pb = parse_playbook(record["yaml"]).model_dump()
    return {"id": record["id"], "revision": revision(record["yaml"]),
            **{key: pb[key] for key in ("name", "version", "description")},
            "rules": [{key: rule.get(key) for key in RULE_FIELDS} for rule in pb["rules"]]}


@router.get("/api/playbooks/{id}/settings")
def settings(id: str):
    record = store.get("playbooks", id)
    if not record:
        raise HTTPException(404, "Playbook not found")
    return view(record)


@router.patch("/api/playbooks/{id}/settings")
def update_settings(id: str, body: SettingsPatch):
    from .main import parse_playbook
    with store.db() as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute("SELECT data FROM playbooks WHERE id=?", (id,)).fetchone()
        if not row:
            raise HTTPException(404, "Playbook not found")
        record = json.loads(row[0])
        if revision(record["yaml"]) != body.revision:
            raise HTTPException(409, "This playbook changed. Reload settings before saving.")
        pb = parse_playbook(record["yaml"]).model_dump()
        for key in body.model_fields_set - {"revision", "rules"}:
            pb[key] = getattr(body, key)
        rules = {rule["id"]: rule for rule in pb["rules"]}
        for patch in body.rules or []:
            if patch.id not in rules:
                raise HTTPException(422, "Unknown rule ID")
            rules[patch.id].update(patch.model_dump(exclude_unset=True))
        text = yaml.safe_dump(pb, sort_keys=False, allow_unicode=True)
        checked = parse_playbook(text)
        record.update(name=checked.name, version=checked.version, description=checked.description, yaml=text)
        connection.execute("UPDATE playbooks SET data=? WHERE id=?", (json.dumps(record), id))
    return view(record)
