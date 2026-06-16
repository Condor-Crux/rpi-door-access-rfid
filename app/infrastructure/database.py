import datetime
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.infrastructure.models import Base

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# WAL mode prevents SSE long-poll from blocking the RFID write loop
@event.listens_for(engine, "connect")
def set_wal_mode(dbapi_connection, connection_record):
    dbapi_connection.execute("PRAGMA journal_mode=WAL")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _run_migrations():
    """Idempotent ALTER TABLE migrations — safe to run on every startup."""
    migrations = [
        "ALTER TABLE users ADD COLUMN deleted_at DATETIME",
        "ALTER TABLE users ADD COLUMN document_type VARCHAR",
        "ALTER TABLE users ADD COLUMN document_number VARCHAR",
        "ALTER TABLE users ADD COLUMN nationality VARCHAR DEFAULT 'AR'",
        "ALTER TABLE companies ADD COLUMN deleted_at DATETIME",
        "ALTER TABLE accounts ADD COLUMN key_type VARCHAR DEFAULT 'particulares'",
        "ALTER TABLE accounts ADD COLUMN charge_value INTEGER",
        "CREATE INDEX IF NOT EXISTS ix_access_logs_timestamp ON access_logs (timestamp)",
        "CREATE INDEX IF NOT EXISTS ix_access_logs_account_id ON access_logs (account_id)",
        "CREATE INDEX IF NOT EXISTS ix_access_logs_event_type ON access_logs (event_type)",
    ]
    with engine.connect() as conn:
        for sql in migrations:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                pass  # Column/index already exists — safe to ignore


def _seed():
    from app.infrastructure.models import CompanyModel
    with SessionLocal() as db:
        if not db.query(CompanyModel).filter_by(name="Particulares").first():
            db.add(CompanyModel(name="Particulares"))
            db.commit()


def init_db():
    Base.metadata.create_all(bind=engine)
    _run_migrations()
    _seed()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
