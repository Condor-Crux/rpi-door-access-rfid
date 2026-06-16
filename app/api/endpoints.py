from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, Response
from app.core.templates import make_templates
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
import datetime

from app.infrastructure.database import get_db
from app.infrastructure.models import AccountModel, CompanyModel, UserModel
from app.domain.entities import Account
from app.core.events import broadcaster
from app.core.security import get_current_admin, get_current_admin_cookie
from app.core.time import utcnow
from app.core.audit import log_audit
from app.api.stats import compute_kpi
from app.api.logs import build_logs_context

router = APIRouter()
templates = make_templates()

# REST API

@router.get("/api/accounts", response_model=List[Account])
def read_accounts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), admin: str = Depends(get_current_admin)):
    accounts = db.query(AccountModel).offset(skip).limit(limit).all()
    return accounts

@router.post("/api/accounts", response_model=Account)
def create_account(account: Account, db: Session = Depends(get_db), admin: str = Depends(get_current_admin)):
    db_account = db.query(AccountModel).filter(AccountModel.account_id == account.account_id).first()
    if db_account:
        raise HTTPException(status_code=400, detail="Account already exists")
    new_account = AccountModel(
        account_id=account.account_id,
        status=account.status,
        expiration_date=account.expiration_date,
        credits=account.credits,
        key_type=account.key_type,
        invoice_number=account.invoice_number if account.key_type == "ticket_carga" else None,
    )
    db.add(new_account)
    db.commit()
    db.refresh(new_account)
    return new_account

@router.put("/api/accounts/{account_id}/recharge")
def recharge_account(account_id: str, amount: int, db: Session = Depends(get_db), admin: str = Depends(get_current_admin)):
    db_account = db.query(AccountModel).filter(AccountModel.account_id == account_id).first()
    if not db_account:
        raise HTTPException(status_code=404, detail="Account not found")
    db_account.credits += amount
    db.commit()
    db.refresh(db_account)
    return {"status": "success", "new_credits": db_account.credits}

# Web UI Routes

@router.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db), admin: str = Depends(get_current_admin_cookie)):
    if not admin:
        return RedirectResponse(url="/login", status_code=303)

    users = (
        db.query(UserModel)
        .options(joinedload(UserModel.company))
        .filter(UserModel.deleted_at == None)
        .order_by(UserModel.first_name, UserModel.last_name)
        .all()
    )
    companies = (
        db.query(CompanyModel)
        .filter(CompanyModel.deleted_at == None)
        .order_by(CompanyModel.id)
        .all()
    )
    kpi = compute_kpi(db)

    return templates.TemplateResponse(request, "index.html", {
        "users": users,
        "companies": companies,
        "kpi": kpi,
        # Seed the dashboard's live log with the most recent entries.
        **build_logs_context(db),
    })


@router.post("/ui/accounts/create")
def ui_create_account(
    request: Request,
    account_id: str = Form(...),
    status: str = Form(...),
    expiration_date: str = Form(...),
    credits: int = Form(...),
    user_id: int = Form(None),
    key_type: str = Form("particulares"),
    invoice_number: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    admin: str = Depends(get_current_admin_cookie)
):
    if not admin:
        return RedirectResponse(url="/login", status_code=303)
    try:
        exp_date_obj = datetime.datetime.fromisoformat(expiration_date)
    except ValueError:
        exp_date_obj = utcnow() + datetime.timedelta(hours=24)

    invoice_number = invoice_number if key_type == "ticket_carga" else None

    account = db.query(AccountModel).filter(AccountModel.account_id == account_id).first()
    created = False
    if not account:
        account = AccountModel(
            account_id=account_id,
            status=status,
            expiration_date=exp_date_obj,
            credits=credits,
            user_id=user_id,
            key_type=key_type,
            invoice_number=invoice_number,
        )
        db.add(account)
        db.commit()
        db.refresh(account)
        created = True
        log_audit(db, "card.created", "admin",
                  f"Tarjeta creada: {account_id}" + (f" → usuario #{user_id}" if user_id else ""),
                  {"account_id": account_id, "status": status, "credits": credits,
                   "expiration_date": exp_date_obj.isoformat(), "user_id": user_id,
                   "key_type": key_type, "invoice_number": invoice_number})
    else:
        # Update existing card's user assignment
        if user_id is not None:
            account.user_id = user_id
            db.commit()
            db.refresh(account)

    if request.headers.get("HX-Request") and user_id:
        # Return updated user detail panel
        from app.infrastructure.models import AccountModel as AM
        user, accounts = _user_with_accounts(db, user_id)
        companies = db.query(CompanyModel).filter(CompanyModel.deleted_at == None).order_by(CompanyModel.id).all()
        response = templates.TemplateResponse(
            request, "_user_detail_panel.html",
            {"user": user, "accounts": accounts, "companies": companies}
        )
        if created:
            response.headers["HX-Trigger"] = "account-created"
        return response

    if request.headers.get("HX-Request"):
        response = templates.TemplateResponse(request, "_account_row.html", {"acc": account})
        if created:
            response.headers["HX-Trigger"] = "account-created"
        return response

    return RedirectResponse(url="/", status_code=303)


def _user_with_accounts(db, user_id):
    user = (
        db.query(UserModel)
        .options(joinedload(UserModel.company))
        .filter(UserModel.id == user_id)
        .first()
    )
    if not user:
        return None, []
    accounts = (
        db.query(AccountModel)
        .filter(AccountModel.user_id == user_id)
        .order_by(AccountModel.expiration_date.desc())
        .all()
    )
    return user, accounts


@router.post("/ui/accounts/{account_id}/recharge")
def ui_recharge_account(
    account_id: str,
    request: Request,
    amount: int = Form(...),
    db: Session = Depends(get_db),
    admin: str = Depends(get_current_admin_cookie),
):
    if not admin:
        return RedirectResponse(url="/login", status_code=303)
    if amount <= 0 or amount > 10000:
        raise HTTPException(status_code=400, detail="amount must be between 1 and 10000")
    account = db.query(AccountModel).filter(AccountModel.account_id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    prev_credits = account.credits
    account.credits += amount
    db.commit()
    db.refresh(account)
    log_audit(db, "card.recharged", "admin",
              f"Créditos recargados: tarjeta {account_id} (+{amount}, total {account.credits})",
              {"account_id": account_id, "amount": amount,
               "credits_before": prev_credits, "credits_after": account.credits})

    if request.headers.get("HX-Request"):
        # If called from user detail panel, return updated panel
        if account.user_id:
            user, accounts = _user_with_accounts(db, account.user_id)
            companies = db.query(CompanyModel).filter(CompanyModel.deleted_at == None).order_by(CompanyModel.id).all()
            return templates.TemplateResponse(
                request, "_user_detail_panel.html",
                {"user": user, "accounts": accounts, "companies": companies}
            )
        return templates.TemplateResponse(request, "_account_row.html", {"acc": account})

    return RedirectResponse(url="/", status_code=303)


@router.post("/ui/accounts/{account_id}/edit")
def ui_edit_account(
    account_id: str,
    request: Request,
    status: str = Form(...),
    expiration_date: str = Form(...),
    credits: int = Form(...),
    key_type: str = Form("particulares"),
    invoice_number: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    admin: str = Depends(get_current_admin_cookie),
):
    if not admin:
        return RedirectResponse(url="/login", status_code=303)
    account = db.query(AccountModel).filter(AccountModel.account_id == account_id).first()
    if not account:
        raise HTTPException(status_code=404)
    try:
        account.expiration_date = datetime.datetime.fromisoformat(expiration_date)
    except ValueError:
        pass
    account.status = status
    account.credits = credits
    account.key_type = key_type
    account.invoice_number = invoice_number if key_type == "ticket_carga" else None
    db.commit()
    db.refresh(account)
    log_audit(db, "card.edited", "admin",
              f"Tarjeta editada: {account_id} — estado={status}, créditos={credits}",
              {"account_id": account_id, "status": status, "credits": credits,
               "expiration_date": account.expiration_date.isoformat(),
               "key_type": key_type, "invoice_number": account.invoice_number})

    if request.headers.get("HX-Request") and account.user_id:
        user, accounts = _user_with_accounts(db, account.user_id)
        companies = db.query(CompanyModel).filter(CompanyModel.deleted_at == None).order_by(CompanyModel.id).all()
        return templates.TemplateResponse(
            request, "_user_detail_panel.html",
            {"user": user, "accounts": accounts, "companies": companies}
        )
    return RedirectResponse(url="/", status_code=303)


@router.delete("/ui/accounts/{account_id}")
def ui_unlink_account(
    account_id: str,
    request: Request,
    db: Session = Depends(get_db),
    admin: str = Depends(get_current_admin_cookie),
):
    if not admin:
        return RedirectResponse(url="/login", status_code=303)
    account = db.query(AccountModel).filter(AccountModel.account_id == account_id).first()
    if not account:
        raise HTTPException(status_code=404)
    user_id = account.user_id
    account.user_id = None
    db.commit()
    log_audit(db, "card.unlinked", "admin",
              f"Tarjeta desvinculada: {account_id}" + (f" (era de usuario #{user_id})" if user_id else ""),
              {"account_id": account_id, "previous_user_id": user_id})

    if request.headers.get("HX-Request") and user_id:
        user, accounts = _user_with_accounts(db, user_id)
        companies = db.query(CompanyModel).filter(CompanyModel.deleted_at == None).order_by(CompanyModel.id).all()
        return templates.TemplateResponse(
            request, "_user_detail_panel.html",
            {"user": user, "accounts": accounts, "companies": companies}
        )
    return Response(status_code=200, content="")


@router.post("/ui/accounts/blanquear")
def ui_blanquear(
    request: Request,
    account_ids: str = Form(...),
    db: Session = Depends(get_db),
    admin: str = Depends(get_current_admin_cookie),
):
    if not admin:
        return RedirectResponse(url="/login", status_code=303)
    ids = [s.strip() for s in account_ids.split(",") if s.strip()]
    updated = db.query(AccountModel).filter(AccountModel.account_id.in_(ids)).all()
    blanqueadas = [acc.account_id for acc in updated]
    for acc in updated:
        acc.user_id = None
    db.commit()
    count = len(updated)
    if ids:
        log_audit(db, "batch.blanquear", "admin",
                  f"Blanqueo de {count} tarjeta(s) — {count} de {len(ids)} encontradas",
                  {"requested": ids, "blanqueadas": blanqueadas, "not_found": [i for i in ids if i not in blanqueadas]})
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(request, "_blanquear_result.html", {"count": count, "ids": ids})
    return RedirectResponse(url="/", status_code=303)


def _render_event_html(event_name: str, data: dict) -> str | None:
    if event_name == "kpi":
        return templates.get_template("_kpi_cards.html").render(kpi=data)
    if event_name == "audit":
        # `data` is already an enrich_log() dict — render one log row.
        return templates.get_template("_log_row.html").render(e=data)
    return None


def _sse_format(event_name: str, html: str) -> str:
    lines = "\n".join(f"data: {line}" for line in html.splitlines())
    return f"event: {event_name}\n{lines}\n\n"


@router.get("/sse/events")
async def sse_events(admin: str = Depends(get_current_admin_cookie)):
    if not admin:
        raise HTTPException(status_code=401, detail="Not authenticated")

    async def stream():
        async for payload in broadcaster.subscribe():
            name = payload["event"]
            if name == "ping":
                yield ": ping\n\n"
                continue
            if name == "ready":
                yield "event: ready\ndata: ok\n\n"
                continue
            html = _render_event_html(name, payload["data"])
            if html is None:
                continue
            yield _sse_format(name, html)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
