from pydantic import BaseModel

class DishCreate(BaseModel):
    name: str
    price: float
    description: str | None = None