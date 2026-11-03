import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.infrastructure.database import get_db
from app.infrastructure.models import AccessLogModel
from app.domain.entities import KPIStats
from app.core.security import get_current_admin_cookie
from app.core.time import utcnow

router = APIRouter()


def _count_window(db: Session, start: datetime.datetime, event_type: str | None = None, reason: str | None = None) -> int:
    q = db.query(func.count(AccessLogModel.id)).filter(AccessLogModel.timestamp >= start)
    if event_type:
        q = q.filter(AccessLogModel.event_type == event_type)
    if reason:
        q = q.filter(AccessLogModel.reason == reason)
    return q.scalar() or 0


def _rate(grant: int, total: int) -> float:
    return round((grant / total) * 100, 1) if total else 0.0


def compute_kpi(db: Session) -> KPIStats:
    now = utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - datetime.timedelta(days=7)
    month_30_start = now - datetime.timedelta(days=30)
    this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    today_total = _count_window(db, today_start)
    today_grant = _count_window(db, today_start, "grant")
    today_deny = _count_window(db, today_start, "deny")

    wk_total = _count_window(db, week_start)
    wk_grant = _count_window(db, week_start, "grant")
    wk_deny = _count_window(db, week_start, "deny")

    m30_total = _count_window(db, month_30_start)
    m30_grant = _count_window(db, month_30_start, "grant")
    m30_deny = _count_window(db, month_30_start, "deny")

    mo_total = _count_window(db, this_month_start)
    mo_grant = _count_window(db, this_month_start, "grant")
    mo_deny = _count_window(db, this_month_start, "deny")

    return KPIStats(
        today_total=today_total,
        today_grant=today_grant,
        today_deny=today_deny,
        today_success_rate=_rate(today_grant, today_total),
        last_7_days_total=wk_total,
        last_7_days_grant=wk_grant,
        last_7_days_deny=wk_deny,
        last_7_days_success_rate=_rate(wk_grant, wk_total),
        last_30_days_total=m30_total,
        last_30_days_grant=m30_grant,
        last_30_days_deny=m30_deny,
        last_30_days_success_rate=_rate(m30_grant, m30_total),
        this_month_total=mo_total,
        this_month_grant=mo_grant,
        this_month_deny=mo_deny,
        this_month_success_rate=_rate(mo_grant, mo_total),
        today_deny_not_found=_count_window(db, today_start, "deny", "Not Found"),
        today_deny_expired=_count_window(db, today_start, "deny", "Expired"),
        today_deny_invalid=_count_window(db, today_start, "deny", "Invalid Status"),
        today_deny_no_credits=_count_window(db, today_start, "deny", "Out of Credits"),
    )


@router.get("/api/stats/kpi", response_model=KPIStats)
def get_kpi_stats(
    db: Session = Depends(get_db),
    admin: str = Depends(get_current_admin_cookie),
):
    if not admin:
        raise HTTPException(status_code=401)
    return compute_kpi(db)
