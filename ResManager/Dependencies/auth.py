from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError

from Config.Security import decode_token
from DataModels.Restruarants import Restaurant
from Dependencies.data import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/ResManager/auth/login")


def get_current_restaurant(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Restaurant:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        restaurant_id: int = payload.get("sub")
        if restaurant_id is None:
            raise credentials_exc
    except JWTError:
        raise credentials_exc

    restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
    if not restaurant:
        raise credentials_exc
    return restaurant