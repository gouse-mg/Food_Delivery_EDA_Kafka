from pydantic import BaseModel, EmailStr


class RestaurantCreate(BaseModel):
    name: str
    email: EmailStr
    password: str                  # plain-text, only on input


class RestaurantLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RestaurantOut(BaseModel):
    id: int
    name: str
    email: str

    class Config:
        from_attributes = True    # Pydantic v2 (use orm_mode=True for v1)