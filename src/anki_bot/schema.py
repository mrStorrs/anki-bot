"""Pydantic v2 models for YAML card schema validation."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

CLOZE_PATTERN = re.compile(r"\{\{c\d+::.+?\}\}")


class BasicCard(BaseModel):
    type: Literal["basic"]
    front: str
    back: str
    tags: list[str] = Field(default_factory=list)

    @field_validator("front", "back")
    @classmethod
    def must_not_be_blank(cls, v: str, info) -> str:
        if not v.strip():
            raise ValueError(f"'{info.field_name}' must not be blank")
        return v


class ClozeCard(BaseModel):
    type: Literal["cloze"]
    text: str
    tags: list[str] = Field(default_factory=list)

    @field_validator("text")
    @classmethod
    def must_contain_cloze_deletion(cls, v: str) -> str:
        if not CLOZE_PATTERN.search(v):
            raise ValueError(
                "Cloze card 'text' must contain at least one cloze deletion "
                "like {{c1::answer}}. Got: " + repr(v[:80])
            )
        return v


Card = Annotated[BasicCard | ClozeCard, Field(discriminator="type")]


class DeckConfig(BaseModel):
    name: str
    description: str = ""
    tags: list[str] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Deck 'name' must not be blank")
        return v


class DeckFile(BaseModel):
    config: DeckConfig
    cards: list[Card]

    @model_validator(mode="after")
    def must_have_cards(self) -> DeckFile:
        if not self.cards:
            raise ValueError("A deck file must contain at least one card")
        return self


def load_deck_file(path: Path) -> DeckFile:
    """Read a YAML deck file and return a validated DeckFile model.

    Raises FileNotFoundError if the path doesn't exist, yaml.YAMLError on
    parse failures, and pydantic.ValidationError on schema violations — all
    with the file path included for actionable diagnostics.
    """
    if not path.exists():
        raise FileNotFoundError(f"Deck file not found: {path}")

    raw = path.read_text(encoding="utf-8")

    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise yaml.YAMLError(f"Invalid YAML in {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"Expected a YAML mapping at top level in {path}, got {type(data).__name__}")

    try:
        return DeckFile.model_validate(data)
    except Exception as exc:
        raise ValueError(f"Validation failed for {path}:\n{exc}") from exc
