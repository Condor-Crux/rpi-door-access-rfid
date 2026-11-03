from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Form, Response
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse, HTMLResponse
from app.core.templates import make_templates
from fastapi import Request

from app.core.config import settings
from app.core.security import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter()
templates = make_templates()

@router.post("/api/login")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.password != settings.SUPER_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": form_data.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html")

@router.post("/ui/login")
def ui_login(
    response: Response,
    username: str = Form("admin"),
    password: str = Form(...),
):
    if password != settings.SUPER_PASSWORD:
        # Redirect back to login upon failure, ideally with an error context
        # But for simplicity, we just redirect.
        return RedirectResponse(url="/login?error=1", status_code=status.HTTP_303_SEE_OTHER)

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": username}, expires_delta=access_token_expires
    )
    
    redirect = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    # Store token in an HttpOnly cookie
    redirect.set_cookie(
        key="access_token", 
        value=f"Bearer {access_token}", 
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax"
    )
    return redirect

@router.get("/ui/logout")
def ui_logout():
    redirect = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    redirect.delete_cookie("access_token")
    return redirect
