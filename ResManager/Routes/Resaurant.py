from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from Models.Restruarant import RestaurantCreate
from Dependencies.data import get_db
from DataModels.Restruarants import Restaurant
from fastapi.responses import HTMLResponse
import Manager
from Config.Security import hash_password   # ✅ add this import
from Cruds.Restuarant import ResService

router = APIRouter(prefix = "/res")

@router.get("/", response_class=HTMLResponse)
async def serve_order_page():
    with open("static/ResAuth.html", "r",encoding="utf-8") as f:
        return HTMLResponse(content=f.read())
    

@router.post("/create-restaurant")
def create_restaurant(payload: RestaurantCreate, db: Session = Depends(get_db)):
    existing = ResService.get_one_by_mail(db,payload)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    restaurant = ResService.add_one(db,payload)
    return restaurant

@router.get("/restaurants")
def get_restaurants(db: Session = Depends(get_db)):
    return db.query(Restaurant).all()


@router.get("/restaurants/{id}")
def get_restaurant(id: int):
    print("Received req")
    res = Manager.res_manager.restaurants[id]
    return {"lat":res.lat,"long":res.longi}