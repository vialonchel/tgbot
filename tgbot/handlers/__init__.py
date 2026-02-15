from aiogram import Router

from .admin import router as admin_router
from .languages import router as languages_router
from .media import router as media_router
from .start import router as start_router
from .stickers import router as stickers_router
from .themes import router as themes_router


router = Router(name="root_handlers")
router.include_router(start_router)
router.include_router(admin_router)
router.include_router(themes_router)
router.include_router(languages_router)
router.include_router(stickers_router)
router.include_router(media_router)
