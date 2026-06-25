from fastapi import APIRouter
from . import auth
from . import Communicate
router = APIRouter(prefix = "/api/PartManager")

router.include_router(auth.router)
router.include_router(Communicate.router)

