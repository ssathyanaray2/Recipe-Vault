from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.api.v1 import recipes, users

v1_router = APIRouter(prefix="/v1")

# Public — no auth required
v1_router.include_router(users.router)

# Protected — auth enforced at the router level for every route below
v1_router.include_router(recipes.router, dependencies=[Depends(get_current_user)])
