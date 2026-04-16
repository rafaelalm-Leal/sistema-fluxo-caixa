from fastapi import FastAPI

from app.database import Base, engine
from app.models.user import User
from app.models.category import Category
from app.models.transaction import Transaction
from app.routes.users import router as users_router
from app.routes.categories import router as categories_router
from app.routes.transactions import router as transactions_router
from app.routes.dashboard import router as dashboard_router

app = FastAPI()

Base.metadata.create_all(bind=engine)

app.include_router(users_router)
app.include_router(categories_router)
app.include_router(transactions_router)
app.include_router(dashboard_router)


@app.get("/")
def pagina_inicial():
    return {"mensagem": "Sistema de fluxo de caixa rodando com FastAPI"}