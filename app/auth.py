from fastapi import Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.models.user import User


def buscar_usuario_logado(request: Request, db: Session) -> User | None:
    user_id = request.session.get("user_id")

    if not user_id:
        return None

    usuario = (
        db.query(User)
        .filter(User.id == user_id, User.ativo == True)
        .first()
    )

    return usuario


def redirecionar_se_nao_logado(request: Request, db: Session):
    usuario = buscar_usuario_logado(request, db)

    if not usuario:
        return RedirectResponse(url="/login", status_code=303)

    return None


def redirecionar_se_nao_for_admin(request: Request, db: Session):
    usuario = buscar_usuario_logado(request, db)

    if not usuario:
        return RedirectResponse(url="/login", status_code=303)

    if not usuario.is_admin:
        return RedirectResponse(url="/dashboard", status_code=303)

    return None