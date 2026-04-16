from fastapi import FastAPI
from src.routes.users.controller import router as users_router
from src.routes.categories.controller import router as categories_router
from src.routes.products.controller import router as products_router
from src.routes.attributes.controller import router as attributes_router

def register_routes(app: FastAPI):
    app.include_router(users_router)
    app.include_router(categories_router)
    app.include_router(products_router)
    app.include_router(attributes_router)