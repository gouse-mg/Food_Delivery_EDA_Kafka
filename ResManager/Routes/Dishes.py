from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from Models.Dish import DishCreate
from Dependencies.data import get_db
from DataModels.Restruarants import Restaurant
from DataModels.Restruarants import Dish
from Dependencies.auth import get_current_restaurant
from Cruds.Restuarant import ResService
from Cruds.Dishes import DishService


router = APIRouter(prefix = "/dishes")

# ... existing restaurant routes ...

# On res/dishes as prefix
@router.post("/create-dish")
def create_dish(payload: DishCreate, db: Session = Depends(get_db),current: Restaurant = Depends(get_current_restaurant)):
    restaurant = ResService.get_one_by_id(db,current.id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    
    dish = DishService.add_one(db,payload,current.id)
    return dish


@router.get("/")
def get_dishes(db: Session = Depends(get_db),current: Restaurant = Depends(get_current_restaurant)):
    restaurant = ResService.get_one_by_id(db,current.id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return db.query(Dish).filter(Dish.restaurant_id == current.id).all()


@router.get("/all-dishes")
def get_dishes(db: Session = Depends(get_db)):
    return db.query(Dish).all()
