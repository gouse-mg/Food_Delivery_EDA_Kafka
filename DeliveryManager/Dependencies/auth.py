from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError

from Config.Security import decode_token
from DataModels.Partners import Partners
from Dependencies.data import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/DelManager/auth/login")


def get_current_partner(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Partners:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        partner_id: int = payload.get("sub")
        if partner_id is None:
            raise credentials_exc
    except JWTError:
        raise credentials_exc

    restaurant = db.query(Partners).filter(Partners.id == partner_id).first()
    if not restaurant:
        raise credentials_exc
    return restaurant