from pydantic import BaseModel, EmailStr


class PartnerCreate(BaseModel):
    name: str
    email: EmailStr
    password: str                  # plain-text, only on input


class PartnerLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PartnerOut(BaseModel):
    id: int
    name: str
    email: str

    class Config:
        from_attributes = True    # Pydantic v2 (use orm_mode=True for v1)