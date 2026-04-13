from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate
from app.security import gerar_hash_senha

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("")
def criar_usuario(user: UserCreate, db: Session = Depends(get_db)):
    usuario_existente = db.query(User).filter(User.email == user.email).first()

    if usuario_existente:
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    novo_usuario = User(
        nome=user.nome,
        email=user.email,
        senha_hash=gerar_hash_senha(user.senha),
        is_admin=user.is_admin,
        ativo=True
    )

    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)

    return {
        "mensagem": "Usuário criado com sucesso",
        "usuario": {
            "id": novo_usuario.id,
            "nome": novo_usuario.nome,
            "email": novo_usuario.email,
            "is_admin": novo_usuario.is_admin,
            "ativo": novo_usuario.ativo
        }
    }


@router.get("")
def listar_usuarios(db: Session = Depends(get_db)):
    usuarios = db.query(User).all()

    return [
        {
            "id": usuario.id,
            "nome": usuario.nome,
            "email": usuario.email,
            "is_admin": usuario.is_admin,
            "ativo": usuario.ativo
        }
        for usuario in usuarios
    ]