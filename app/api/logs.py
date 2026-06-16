import datetime
import json
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from app.core.templates import make_templates
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.infrastructure.models import AuditLogModel
from app.core.security import get_current_admin_cookie

router = APIRouter()
templates = make_templates()

PER_PAGE = 50

# Human-readable event type labels (Spanish)
EVENT_LABELS = {
    "rfid.grant":      "Acceso concedido",
    "rfid.deny":       "Acceso denegado",
    "user.created":    "Usuario creado",
    "user.deleted":    "Usuario eliminado",
    "company.created": "Empresa creada",
    "company.deleted": "Empresa eliminada",
    "card.created":    "Tarjeta creada",
    "card.edited":     "Tarjeta editada",
    "card.recharged":  "Créditos recargados",
    "card.unlinked":   "Tarjeta desvinculada",
    "batch.blanquear": "Blanqueo de tarjetas",
}

# Event type categories for UI grouping
EVENT_CATEGORIES = {
    "rfid":    ["rfid.grant", "rfid.deny"],
    "users":   ["user.created", "user.deleted"],
    "companies": ["company.created", "company.deleted"],
    "cards":   ["card.created", "card.edited", "card.recharged", "card.unlinked", "batch.blanquear"],
}


_KEY_TYPE_LABELS = {
    "particulares": "Particular",
    "cuenta_corriente": "Cta. Cte.",
    "ticket_carga": "Ticket carga",
}


def _enrich(row):
    """Flatten a log row into columns (objeto + detalle) so the table needs
    no expandable details. The event type is NOT repeated in the text — it
    lives in the icon column."""
    try:
        d = json.loads(row.details) if row.details else {}
    except (ValueError, TypeError):
        d = {}
    et = row.event_type
    objeto = ""
    detalle = ""

    def kt(v):
        return _KEY_TYPE_LABELS.get(v, v)

    def fmt_exp(v):
        """Format an ISO expiration timestamp as 'YYYY-MM-DD HH:MM'."""
        if not v:
            return ""
        try:
            return datetime.datetime.fromisoformat(v).strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            return str(v)

    if et == "rfid.grant":
        objeto = d.get("account_id", "")
        parts = []
        cr = d.get("credits_remaining")
        if cr is not None:
            parts.append(f"{cr} créd. restantes")
        if d.get("key_type"):
            parts.append(kt(d["key_type"]))
        detalle = " · ".join(parts)
    elif et == "rfid.deny":
        objeto = d.get("account_id", "")
        detalle = d.get("reason", "")
    elif et == "card.recharged":
        objeto = d.get("account_id", "")
        detalle = f"+{d.get('amount')} créd ({d.get('credits_before')} → {d.get('credits_after')})"
    elif et == "card.created":
        objeto = d.get("account_id", "")
        parts = []
        if d.get("user_id"):
            parts.append(f"usuario #{d['user_id']}")
        if d.get("status"):
            parts.append(f"estado {d['status']}")
        if d.get("credits") is not None:
            parts.append(f"{d['credits']} créd")
        if d.get("key_type"):
            parts.append(kt(d["key_type"]))
        if d.get("invoice_number"):
            parts.append(f"ticket #{d['invoice_number']}")
        if d.get("expiration_date"):
            parts.append(f"vence {fmt_exp(d['expiration_date'])}")
        detalle = " · ".join(parts)
    elif et == "card.edited":
        objeto = d.get("account_id", "")
        parts = []
        if d.get("status"):
            parts.append(f"estado {d['status']}")
        if d.get("credits") is not None:
            parts.append(f"{d['credits']} créd")
        if d.get("key_type"):
            parts.append(kt(d["key_type"]))
        if d.get("invoice_number"):
            parts.append(f"ticket #{d['invoice_number']}")
        if d.get("expiration_date"):
            parts.append(f"vence {fmt_exp(d['expiration_date'])}")
        detalle = " · ".join(parts)
    elif et == "card.unlinked":
        objeto = d.get("account_id", "")
        pu = d.get("previous_user_id")
        detalle = f"era de usuario #{pu}" if pu else ""
    elif et == "user.created":
        name = (f"{d.get('first_name', '')} {d.get('last_name', '')}").strip()
        objeto = name or d.get("name", "")
        parts = []
        if d.get("company_name"):
            parts.append(d["company_name"])
        if d.get("document_number"):
            parts.append(f"{d.get('document_type') or 'Doc'} {d['document_number']}")
        if d.get("nationality"):
            parts.append(d["nationality"])
        if d.get("email"):
            parts.append(d["email"])
        detalle = " · ".join(parts)
    elif et == "user.deleted":
        objeto = d.get("name", "") or d.get("user", "")
        if d.get("user_id"):
            detalle = f"#{d['user_id']}"
    elif et == "company.created":
        objeto = d.get("name", "")
        if d.get("company_id"):
            detalle = f"#{d['company_id']}"
    elif et == "company.deleted":
        objeto = d.get("name", "")
        if d.get("company_id"):
            detalle = f"#{d['company_id']}"
    elif et == "batch.blanquear":
        b = d.get("blanqueadas") or []
        nf = d.get("not_found") or []
        objeto = ", ".join(str(x) for x in b[:5]) + ("…" if len(b) > 5 else "")
        parts = [f"{len(b)} blanqueada(s)"]
        if nf:
            parts.append(f"{len(nf)} no encontrada(s)")
        detalle = " · ".join(parts) if b or nf else row.summary

    # Fallback — derive from the human summary ("X — Y")
    if not objeto and not detalle:
        s = row.summary or ""
        if "—" in s:
            objeto = s.split("—", 1)[1].strip()
        else:
            detalle = s

    return {
        "timestamp": row.timestamp,
        "event_type": et,
        "actor": row.actor,
        "objeto": objeto,
        "detalle": detalle,
    }


def _build_query(db: Session, event_type: str, actor: str, text: str, date_from: str, date_to: str):
    query = db.query(AuditLogModel).order_by(AuditLogModel.timestamp.desc())

    if event_type and event_type != "all":
        if event_type in EVENT_CATEGORIES:
            query = query.filter(AuditLogModel.event_type.in_(EVENT_CATEGORIES[event_type]))
        else:
            query = query.filter(AuditLogModel.event_type == event_type)

    if actor and actor != "all":
        query = query.filter(AuditLogModel.actor == actor)

    if text.strip():
        pattern = f"%{text.strip()}%"
        query = query.filter(AuditLogModel.summary.ilike(pattern))

    if date_from.strip():
        try:
            dt = datetime.datetime.strptime(date_from.strip(), "%Y-%m-%d")
            query = query.filter(AuditLogModel.timestamp >= dt)
        except ValueError:
            pass

    if date_to.strip():
        try:
            dt = datetime.datetime.strptime(date_to.strip(), "%Y-%m-%d") + datetime.timedelta(days=1)
            query = query.filter(AuditLogModel.timestamp < dt)
        except ValueError:
            pass

    return query


@router.get("/ui/logs", response_class=HTMLResponse)
def ui_logs(
    request: Request,
    event_type: str = "all",
    actor: str = "all",
    text: str = "",
    date_from: str = "",
    date_to: str = "",
    page: int = 1,
    db: Session = Depends(get_db),
    admin: str = Depends(get_current_admin_cookie),
):
    if not admin:
        raise HTTPException(status_code=401)

    query = _build_query(db, event_type, actor, text, date_from, date_to)
    total = query.count()
    rows = query.offset((page - 1) * PER_PAGE).limit(PER_PAGE).all()

    has_more = (page * PER_PAGE) < total
    filters = {
        "event_type": event_type,
        "actor": actor,
        "text": text,
        "date_from": date_from,
        "date_to": date_to,
    }

    context = {
        "logs": [_enrich(r) for r in rows],
        "has_more": has_more,
        "next_page": page + 1,
        "total": total,
        "filters": filters,
        "event_labels": EVENT_LABELS,
        "event_categories": list(EVENT_CATEGORIES.keys()),
        "all_event_types": list(EVENT_LABELS.keys()),
    }

    is_htmx = request.headers.get("HX-Request")
    template = "_logs_table.html" if is_htmx else "_tab_logs.html"
    return templates.TemplateResponse(request, template, context)
