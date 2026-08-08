"""Import all models so Alembic autogenerate and metadata see them."""

from app.db.base import Base  # noqa: F401
from app.models.agents import Agent, Tool, agent_tools  # noqa: F401
from app.models.audit import AuditEvent, ExternalAIAudit, ExternalAIEscalation  # noqa: F401
from app.models.chat import Conversation, Message, MessageSource  # noqa: F401
from app.models.documents import (  # noqa: F401
    Document,
    DocumentChunk,
    DocumentPermission,
    DocumentVersion,
    Embedding,
    KnowledgeBase,
)
from app.models.iam import (  # noqa: F401
    Department,
    Permission,
    Role,
    User,
    role_permissions,
    user_roles,
)
from app.models.system import Integration, Job, Notification, SystemSetting  # noqa: F401
from app.models.vehicles import (  # noqa: F401
    InsuranceConflict,
    InsurancePolicy,
    Vehicle,
    VehicleAlert,
    VehicleComplianceRule,
    VehicleDocument,
    VehicleDocumentExtraction,
    VehicleDocumentVersion,
)

__all__ = ["Base"]
