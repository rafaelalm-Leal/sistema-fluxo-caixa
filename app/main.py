from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

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

import os
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "chave-local-apenas-para-desenvolvimento")
)

Base.metadata.create_all(bind=engine)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(users_router)
app.include_router(categories_router)
app.include_router(transactions_router)
app.include_router(dashboard_router)
app.include_router(pages_router)


@app.get("/")
def pagina_inicial(request: Request):
    user_id = request.session.get("user_id")

    if user_id:
        return RedirectResponse(url="/dashboard", status_code=303)
    
    return RedirectResponse(url="/login", status_code=303)

@app.get("/health")
def health():
    return {"status": "ok"}