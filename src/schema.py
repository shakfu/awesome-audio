"""Schema validation for awesome-audio entries using Pydantic."""

from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, field_validator, model_validator


# Canonical categories - entries should use one of these
CATEGORIES = {
    "ableton",
    "algorithmic-music",
    "analysis",
    "audio-driver",
    "audio-framework",
    "audio-interface",
    "augmentation",
    "beatmatching",
    "chuck",
    "csound",
    "daw",
    "dsp",
    "editor",
    "fx",
    "livecoding",
    "looping",
    "midi",
    "monome",
    "music-programming",
    "plugins",
    "random",
    "resampling",
    "sequencer",
    "speech",
    "supercollider",
    "synthesis",
    "timestretching",
    "tracker",
    "utility",
    "visualization",
    "wavetables",
}


class EntrySchema(BaseModel):
    """Schema for a single entry in the awesome-audio list."""

    name: str
    category: str
    desc: str
    url: Optional[str] = None
    repo: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_not_url(cls, v: str) -> str:
        """Name should not be a URL."""
        if v.startswith("http://") or v.startswith("https://"):
            raise ValueError(f"name should not be a URL: {v}")
        return v

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        """Name should not be empty."""
        if not v or not v.strip():
            raise ValueError("name cannot be empty")
        return v.strip()

    @model_validator(mode="after")
    def must_have_url_or_repo(self) -> "EntrySchema":
        """Entry must have at least one of url or repo."""
        if not self.url and not self.repo:
            raise ValueError(f"entry '{self.name}' must have url or repo")
        return self


class ValidationResult:
    """Result of validating entries."""

    def __init__(self):
        self.valid: list[EntrySchema] = []
        self.errors: list[tuple[int, dict, str]] = []
        self.warnings: list[tuple[int, dict, str]] = []
        self.duplicates: list[tuple[str, list[int]]] = []

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def summary(self) -> str:
        lines = [
            f"Valid entries: {len(self.valid)}",
            f"Errors: {len(self.errors)}",
            f"Warnings: {len(self.warnings)}",
            f"Duplicates: {len(self.duplicates)}",
        ]
        return "\n".join(lines)


def validate_entries(entries: list[dict]) -> ValidationResult:
    """Validate a list of entry dictionaries."""
    result = ValidationResult()
    seen_names: dict[str, list[int]] = {}

    for idx, entry in enumerate(entries):
        name = entry.get("name", "")

        # Track duplicates
        if name:
            if name not in seen_names:
                seen_names[name] = []
            seen_names[name].append(idx + 1)  # 1-indexed for human readability

        # Validate entry
        try:
            validated = EntrySchema(**entry)
            result.valid.append(validated)

            # Check for non-canonical category (warning, not error)
            # Allow multi-word categories but warn if primary word not in set
            primary_cat = validated.category.split()[0].lower()
            if primary_cat not in CATEGORIES:
                result.warnings.append(
                    (idx + 1, entry, f"non-canonical category: {validated.category}")
                )
        except Exception as e:
            result.errors.append((idx + 1, entry, str(e)))

    # Record duplicates
    for name, indices in seen_names.items():
        if len(indices) > 1:
            result.duplicates.append((name, indices))

    return result


def load_and_validate(path: Path) -> ValidationResult:
    """Load a YAML file and validate its entries."""
    with open(path) as f:
        entries = yaml.safe_load(f)
    return validate_entries(entries)


if __name__ == "__main__":
    # Run validation on entries.yml
    entries_path = Path(__file__).parent.parent / "data" / "entries.yml"
    result = load_and_validate(entries_path)

    print(result.summary())
    print()

    if result.errors:
        print("ERRORS:")
        for idx, entry, error in result.errors:
            print(f"  Line ~{idx}: {entry.get('name', 'UNKNOWN')}: {error}")
        print()

    if result.duplicates:
        print("DUPLICATES:")
        for name, indices in result.duplicates:
            print(f"  '{name}' appears at entries: {indices}")
        print()

    if result.warnings:
        print("WARNINGS:")
        for idx, entry, warning in result.warnings:
            print(f"  Line ~{idx}: {entry.get('name', 'UNKNOWN')}: {warning}")
