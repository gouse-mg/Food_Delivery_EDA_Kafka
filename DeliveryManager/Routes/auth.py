import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'outside_dir')))

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.responses import HTMLResponse

from Config.Security import hash_password, verify_password, create_access_token
from DataModels.Partners import Partners
from Dependencies.data import get_db
from Dependencies.auth import get_current_partner
from Models.Partners import PartnerCreate, PartnerLogin, TokenResponse, PartnerOut

router = APIRouter(prefix = "/auth",tags=["Auth"])

@router.get("/", response_class=HTMLResponse)
async def serve_order_page():
    with open("static/PartAuth.html", "r",encoding="utf-8") as f:
        return HTMLResponse(content=f.read())
    

@router.post("/register", response_model=PartnerOut, status_code=201)
def register(payload: PartnerCreate, db: Session = Depends(get_db)):
    if db.query(Partners).filter(Partners.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    partner = Partners(
        name=payload.name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(partner)
    db.commit()
    db.refresh(partner)
    return partner


@router.post("/login", response_model=TokenResponse)
def login(payload: PartnerLogin, db: Session = Depends(get_db)):
    partner = db.query(Partners).filter(Partners.email == payload.email).first()

    # Deliberately vague error — don't leak whether the email exists
    if not partner or not verify_password(payload.password, partner.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token({"sub": partner.id})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=PartnerOut)
def me(current: Partners = Depends(get_current_partner)):
    return current