from sqlalchemy.exc import SQLAlchemyError
from DataModels.Restruarants import Restaurant
from Config.Security import hash_password


class ResService:

    @staticmethod
    def add_one(db, payload):
        try:
            restaurant = Restaurant(
                name=payload.name,
                email=payload.email,
                hashed_password=hash_password(payload.password),
            )
            db.add(restaurant)
            db.commit()
            db.refresh(restaurant)
            return restaurant
        except SQLAlchemyError as e:
            db.rollback()
            raise RuntimeError(f"Database error while adding restaurant: {e}")

    @staticmethod
    def get_one_by_mail(db, payload):
        try:
            return db.query(Restaurant).filter(Restaurant.email == payload.email).first()
        except SQLAlchemyError as e:
            raise RuntimeError(f"Database error while fetching restaurant {payload.id}: {e}")
        
    @staticmethod
    def get_one_by_id(db, id):
        try:
            return db.query(Restaurant).filter(Restaurant.id == id).first()
        except SQLAlchemyError as e:
            raise RuntimeError(f"Database error while fetching restaurant {id}: {e}")

    @staticmethod
    def get_many(db, ids: list[int]):
        try:
            return db.query(Restaurant).filter(Restaurant.id.in_(ids)).all()
        except SQLAlchemyError as e:
            raise RuntimeError(f"Database error while fetching dishes: {e}")

    @staticmethod
    def update_one(db, payload):
        try:
            restaurant = db.query(Restaurant).filter(Restaurant.id == payload.id).first()
            if not restaurant:
                return None

            if payload.name:
                restaurant.name = payload.name
            if payload.email:
                restaurant.email = payload.email
            if payload.password:
                restaurant.hashed_password = hash_password(payload.password)

            db.commit()
            db.refresh(restaurant)
            return restaurant
        except SQLAlchemyError as e:
            db.rollback()
            raise RuntimeError(f"Database error while updating restaurant {payload.id}: {e}")

    @staticmethod
    def delete_one(db, payload):
        try:
            restaurant = db.query(Restaurant).filter(Restaurant.id == payload.id).first()
            if not restaurant:
                return None

            db.delete(restaurant)
            db.commit()
            return restaurant
        except SQLAlchemyError as e:
            db.rollback()
            raise RuntimeError(f"Database error while deleting restaurant {payload.id}: {e}")