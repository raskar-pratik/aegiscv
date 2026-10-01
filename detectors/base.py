"""Detector extension interface."""
from typing import Protocol, Any
from core.schemas import Finding


class AssuranceDetector(Protocol):
    def scan(self, asset: Any, context: dict) -> list[Finding]: ...
