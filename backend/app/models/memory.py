from sqlalchemy import Float, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPkMixin


class UserMemory(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "user_memories"

    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # dietary_restriction / allergy / dislike / preference
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, server_default=text("1.0"), nullable=False)
    # explicit | inferred
    source: Mapped[str] = mapped_column(
        String(20), server_default=text("'explicit'"), nullable=False
    )
