from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ValidationResult:
    ok: bool
    confidence: float
    reason: Optional[str] = None


def validate_birth_date(birth_date: str | None) -> ValidationResult:
    if not birth_date:
        return ValidationResult(
            ok=False, confidence=0.0, reason="Missing birth date from Wikidata."
        )
    if len(birth_date) != 10 or birth_date[4] != "-" or birth_date[7] != "-":
        return ValidationResult(
            ok=False,
            confidence=0.2,
            reason=f"Birth date not ISO YYYY-MM-DD: {birth_date}",
        )
    return ValidationResult(ok=True, confidence=0.98, reason=None)
