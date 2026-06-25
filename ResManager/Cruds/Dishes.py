from sqlalchemy.exc import SQLAlchemyError
from DataModels.Restruarants import Dish


class DishService:

    # ── CREATE ────────────────────────────────────────────────────────────────

    @staticmethod
    def add_one(db, payload, res_id: int):
        try:
            dish = Dish(
                name=payload.name,
                price=payload.price,
                description=payload.description,
                restaurant_id=res_id,
            )
            db.add(dish)
            db.commit()
            db.refresh(dish)
            return dish
        except SQLAlchemyError as e:
            db.rollback()
            raise RuntimeError(f"Database error while adding dish: {e}")

    # ── READ ──────────────────────────────────────────────────────────────────

    @staticmethod
    def get_one_id(db,id):
        try:
            return db.query(Dish).filter(Dish.id == id).first()
        except SQLAlchemyError as e:
            raise RuntimeError(f"Database error while fetching dish {id}: {e}")
        


    @staticmethod
    def get_many(db, ids: list[int]):
        try:
            return db.query(Dish).filter(Dish.id.in_(ids)).all()
        except SQLAlchemyError as e:
            raise RuntimeError(f"Database error while fetching dishes: {e}")

    # ── UPDATE ────────────────────────────────────────────────────────────────

    @staticmethod
    def update_one(db, payload):
        try:
            dish = db.query(Dish).filter(Dish.id == payload.id).first()
            if not dish:
                return None

            if payload.name:
                dish.name = payload.name
            if payload.price:
                dish.price = payload.price
            if payload.description:
                dish.description = payload.description

            db.commit()
            db.refresh(dish)
            return dish
        except SQLAlchemyError as e:
            db.rollback()
            raise RuntimeError(f"Database error while updating dish {payload.id}: {e}")

    # ── DELETE ────────────────────────────────────────────────────────────────

    @staticmethod
    def delete_one(db, id):
        try:
            dish = db.query(Dish).filter(Dish.id == id).first()
            if not dish:
                return None

            db.delete(dish)
            db.commit()
            return dish
        except SQLAlchemyError as e:
            db.rollback()
            raise RuntimeError(f"Database error while deleting dish {id}: {e}")