# Alle Models importieren damit SQLAlchemy Metadata vollständig ist
# (wichtig für Alembic autogenerate)
from app.models.workspace import Workspace
from app.models.user import User
from app.models.meeting import Meeting, MeetingStatus
from app.models.action_item import ActionItem
from app.models.embedding import Embedding

__all__ = ["Workspace", "User", "Meeting", "MeetingStatus", "ActionItem", "Embedding"]
