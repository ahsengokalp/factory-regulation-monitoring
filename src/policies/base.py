from __future__ import annotations

from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import List

from src.core.models import GazetteItem


@dataclass(frozen=True)
class PolicyDecision:
    is_relevant: bool
    score: int
    reasons: List[str]


class DepartmentPolicy(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def evaluate_title(self, item: GazetteItem) -> PolicyDecision:
        ...
