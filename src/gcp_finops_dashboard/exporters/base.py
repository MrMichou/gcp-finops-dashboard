"""Exporter abstraction shared by all report formats."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from gcp_finops_dashboard.models import DashboardData


class Exporter(ABC):
    """Writes a :class:`DashboardData` to a file in a specific format."""

    #: File extension (without the dot) this exporter produces.
    extension: str = ""

    @abstractmethod
    def export(self, data: DashboardData, out_path: Path) -> Path:
        """Write ``data`` to ``out_path`` and return the path written."""
        raise NotImplementedError
