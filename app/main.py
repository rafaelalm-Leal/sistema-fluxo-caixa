from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.models.user import User
from app.models.category import Category
from app.models.transaction import Transaction
from app.routes.users import router as users_router
from app.routes.categories import router as categories_router
from app.routes.transactions import router as transactions_router
from app.routes.dashboard import router as dashboard_router
from app.routes.pages import router as pages_router

app = FastAPI()

Base.metadata.create_all(bind=engine)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(users_router)
app.include_router(categories_router)
app.include_router(transactions_router)
app.include_router(dashboard_router)
app.include_router(pages_router)


@app.get("/")
def pagina_inicial():
    return RedirectResponse(url="/dashboard")