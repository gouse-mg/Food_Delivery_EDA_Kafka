from sqlalchemy import Column, Integer, String, ForeignKey,Float
from sqlalchemy.orm import relationship
from database import Base


# DataModels/Restruarants.py

from sqlalchemy.orm import relationship

class Restaurant(Base):
    __tablename__ = "restaurants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    dishes = relationship("Dish", back_populates="restaurant")  # ✅ must match Dish.restaurant

class Dish(Base):
    __tablename__ = "dishes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    description = Column(String, nullable=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)  # ✅ this was missing

    restaurant = relationship("Restaurant", back_populates="dishes")