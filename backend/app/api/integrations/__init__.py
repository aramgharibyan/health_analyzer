from fastapi import APIRouter
from app.api.integrations import whoop, withings, fitbod, yazio, renpho, braun, larq, apple_health

router = APIRouter(prefix="/integrations", tags=["Integrations"])

router.include_router(whoop.router)
router.include_router(withings.router)
router.include_router(fitbod.router)
router.include_router(yazio.router)
router.include_router(renpho.router)
router.include_router(braun.router)
router.include_router(larq.router)
router.include_router(apple_health.router)
