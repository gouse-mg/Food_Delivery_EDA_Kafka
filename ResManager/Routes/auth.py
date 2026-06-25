import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'outside_dir')))

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from Config.Security import hash_password, verify_password, create_access_token
from DataModels.Restruarants import Restaurant
from Dependencies.data import get_db
from Dependencies.auth import get_current_restaurant
from Models.Restruarant import RestaurantCreate, RestaurantLogin, TokenResponse, RestaurantOut

router = APIRouter(prefix = "/auth",tags=["Auth"])


@router.post("/register", response_model=RestaurantOut, status_code=201)
def register(payload: RestaurantCreate, db: Session = Depends(get_db)):
    if db.query(Restaurant).filter(Restaurant.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    restaurant = Restaurant(
        name=payload.name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(restaurant)
    db.commit()
    db.refresh(restaurant)
    return restaurant


@router.post("/login", response_model=TokenResponse)
def login(payload: RestaurantLogin, db: Session = Depends(get_db)):
    restaurant = db.query(Restaurant).filter(Restaurant.email == payload.email).first()

    # Deliberately vague error — don't leak whether the email exists
    if not restaurant or not verify_password(payload.password, restaurant.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token({"sub": restaurant.id})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=RestaurantOut)
def me(current: Restaurant = Depends(get_current_restaurant)):
    return current