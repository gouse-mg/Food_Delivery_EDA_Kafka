from fastapi import APIRouter
from Routes import  auth,Communication,Resaurant,Dishes 


router = APIRouter(prefix = "/api/ResManager")

router.include_router(auth.router)
router.include_router(Communication.router)
router.include_router(Resaurant.router)
router.include_router(Dishes.router)
