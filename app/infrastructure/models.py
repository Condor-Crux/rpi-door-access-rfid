import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing import Optional

from app.core.time import utcnow

class Base(DeclarativeBase):
    pass

class CompanyModel(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String)
    deleted_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True, default=None)

class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    first_name: Mapped[str] = mapped_column(String)
    last_name: Mapped[str] = mapped_column(String)
    email: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    company_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("companies.id"), nullable=True)
    document_type: Mapped[Optional[str]] = mapped_column(String, nullable=True, default=None)
    document_number: Mapped[Optional[str]] = mapped_column(String, nullable=True, default=None)
    nationality: Mapped[str] = mapped_column(String, default="AR")
    deleted_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True, default=None)

    company = relationship("CompanyModel")

class AccountModel(Base):
    __tablename__ = "accounts"

    account_id: Mapped[str] = mapped_column(String, primary_key=True)
    status: Mapped[str] = mapped_column(String, default="active") # "active" or "inactive"
    expiration_date: Mapped[datetime.datetime] = mapped_column(DateTime)
    credits: Mapped[int] = mapped_column(Integer, default=0)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    # "particulares", "cuenta_corriente" or "ticket_carga"
    key_type: Mapped[str] = mapped_column(String, default="particulares")
    # Número del ticket/comprobante de carga (solo aplica si key_type == "ticket_carga")
    invoice_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=None)

    user = relationship("UserModel")

class AccessLogModel(Base):
    __tablename__ = "access_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)
    account_id: Mapped[str] = mapped_column(String)
    event_type: Mapped[str] = mapped_column(String) # "grant" or "deny"
    reason: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    __table_args__ = (
        Index("ix_access_logs_timestamp", "timestamp"),
        Index("ix_access_logs_account_id", "account_id"),
        Index("ix_access_logs_event_type", "event_type"),
    )


class AuditLogModel(Base):
    """Immutable system-wide audit trail. Never deleted or updated."""
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)
    # Semantic event type: rfid.grant, rfid.deny, user.created, user.deleted,
    # company.created, company.deleted, card.created, card.edited,
    # card.recharged, card.unlinked, batch.blanquear
    event_type: Mapped[str] = mapped_column(String)
    actor: Mapped[str] = mapped_column(String)  # "system" or "admin"
    summary: Mapped[str] = mapped_column(String)  # human-readable one-liner
    details: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # JSON text

    __table_args__ = (
        Index("ix_audit_logs_timestamp", "timestamp"),
        Index("ix_audit_logs_event_type", "event_type"),
        Index("ix_audit_logs_actor", "actor"),
    )
