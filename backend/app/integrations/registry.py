"""Registry of declared connectors (Phase 2/3) and DB seeding of integrations.

Each connector is declared with a real spec but backed by NotImplementedConnector
until wired. seed_integrations() records them as disabled rows so the Admin UI can
list them honestly as "Coming Later".
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.base import Connector, ConnectorSpec, NotImplementedConnector
from app.models.system import Integration

SPECS: list[ConnectorSpec] = [
    ConnectorSpec("entra", "Microsoft Entra ID", 2,
                  "OIDC SSO + user/group sync mapping to MuniAI users/departments/roles.",
                  ["auth", "user_sync", "group_sync"]),
    ConnectorSpec("sharepoint", "SharePoint / OneDrive", 2,
                  "Import documents while preserving access permissions.",
                  ["document_sync", "permission_preserving"]),
    ConnectorSpec("outlook", "Outlook / Microsoft 365 Mail", 2,
                  "Search, summarize and find attachments (never auto-send).",
                  ["search", "summarize"]),
    ConnectorSpec("vehicle_system", "Vehicle Management System", 2,
                  "Connect to the municipality's dedicated vehicle system via API.",
                  ["read_vehicle", "list_renewals"]),
    ConnectorSpec("asset_system", "Asset Management System", 2,
                  "Municipal inventory lookups (QR/asset id).",
                  ["read_asset"]),
    ConnectorSpec("gis", "GIS / Street Intelligence", 3,
                  "Consume structured detected hazards/assets from a CV engine.",
                  ["list_hazards", "list_assets"]),
    ConnectorSpec("whatsapp", "WhatsApp Business", 3,
                  "Resident notifications/templates (kept separate from core AI).",
                  ["send_template"]),
]


def get_connector(key: str) -> Connector:
    spec = next((s for s in SPECS if s.key == key), None)
    if spec is None:
        raise KeyError(f"Unknown connector '{key}'")
    return NotImplementedConnector(spec)


def seed_integrations(db: Session) -> None:
    for spec in SPECS:
        if not db.scalar(select(Integration).where(Integration.kind == spec.key)):
            db.add(Integration(
                name=spec.name, kind=spec.key, enabled=False,
                status="not_configured",
                config={"phase": spec.phase, "capabilities": spec.capabilities},
            ))
    db.commit()
