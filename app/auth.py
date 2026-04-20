from fastapi import HTTPException, Request
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


def exigir_usuario_logado(request: Request, db: Session) -> User:
    usuario = buscar_usuario_logado(request, db)

    if not usuario:
        raise HTTPException(status_code=401, detail="Usuário não autenticado")

    return usuario


def exigir_admin(request: Request, db: Session) -> User:
    usuario = exigir_usuario_logado(request, db)

    if not usuario.is_admin:
        raise HTTPException(status_code=403, detail="Acesso permitido apenas para administrador")

    return usuario