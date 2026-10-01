"""Common evidence schema; confidence is heuristic unless explicitly stated."""
from dataclasses import dataclass, field, asdict
from typing import Any
from uuid import uuid4


def severity(score: float) -> str:
    return next((name for ceiling, name in [(20,"LOW"),(40,"GUARDED"),(60,"MODERATE"),(80,"HIGH"),(100,"CRITICAL")] if score <= ceiling), "CRITICAL")


@dataclass
class Finding:
    detector: str
    category: str
    attack_class: str
    asset_id: str
    risk_score: float
    confidence: float
    reason: str
    evidence: dict[str, Any]
    status: str = "SUCCESS"
    asset_type: str = "IMAGE"
    limitations: list[str] = field(default_factory=list)
    finding_id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self):
        if not 0 <= self.risk_score <= 100 or not 0 <= self.confidence <= 1:
            raise ValueError("Risk or confidence out of range")
        if self.status not in {"SUCCESS", "WARNING", "UNAVAILABLE", "FAILED"}:
            raise ValueError("Invalid detector status")

    def to_dict(self):
        from core.quality import annotate
        return annotate(dict(asdict(self), severity=severity(self.risk_score), recommended_action=("REVIEW" if self.status != "SUCCESS" else "QUARANTINE" if self.risk_score > 80 else "REVIEW" if self.risk_score > 20 else "ACCEPT")))
