"""Connector interface layer for external municipal systems (spec §61).

MuniAI does not reimplement systems the municipality already owns — it connects to
them through a tool/API layer and becomes the intelligence layer above them.

These are REAL, typed interfaces defining the contract each connector must honor.
The concrete Phase 2/3 connectors are declared here but are intentionally NOT
wired to live external services (that requires each system's credentials and
endpoints). They register as disabled integrations and are surfaced honestly as
"Coming Later" — never faked as working.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ConnectorStatus:
    name: str
    available: bool
    detail: str = ""


@dataclass
class ConnectorSpec:
    key: str            # stable identifier, e.g. "entra"
    name: str           # display name
    phase: int          # 2 or 3
    description: str
    capabilities: list[str] = field(default_factory=list)


class Connector(ABC):
    """Base class every external-system connector implements."""

    spec: ConnectorSpec

    @abstractmethod
    async def health(self) -> ConnectorStatus:
        """Report whether the external system is reachable/configured."""

    def is_implemented(self) -> bool:
        """False for Phase 2/3 stubs until wired to a real system."""
        return False


class NotImplementedConnector(Connector):
    """A declared-but-unwired connector. Calling its operations raises clearly so
    nothing silently pretends to work."""

    def __init__(self, spec: ConnectorSpec):
        self.spec = spec

    async def health(self) -> ConnectorStatus:
        return ConnectorStatus(self.spec.name, available=False, detail="Not configured (Coming Later)")

    def __getattr__(self, item: str):  # any operation call
        def _unavailable(*_a, **_k):
            raise NotImplementedError(
                f"Connector '{self.spec.key}' is a declared interface and is not "
                f"implemented yet (Phase {self.spec.phase})."
            )
        return _unavailable
