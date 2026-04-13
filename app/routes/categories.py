from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.category import Category
from app.schemas.category import CategoryCreate

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.post("")
def criar_categoria(category: CategoryCreate, db: Session = Depends(get_db)):
    categoria_existente = (
        db.query(Category)
        .filter(
            Category.nome == category.nome,
            Category.tipo == category.tipo
        )
        .first()
    )

    if categoria_existente:
        raise HTTPException(
            status_code=400,
            detail="Já existe uma categoria com esse nome e tipo"
        )

    nova_categoria = Category(
        nome=category.nome,
        tipo=category.tipo,
        ativa=True
    )

    db.add(nova_categoria)
    db.commit()
    db.refresh(nova_categoria)

    return {
        "mensagem": "Categoria criada com sucesso",
        "categoria": {
            "id": nova_categoria.id,
            "nome": nova_categoria.nome,
            "tipo": nova_categoria.tipo,
            "ativa": nova_categoria.ativa
        }
    }


@router.get("")
def listar_categorias(db: Session = Depends(get_db)):
    categorias = db.query(Category).all()

    return [
        {
            "id": categoria.id,
            "nome": categoria.nome,
            "tipo": categoria.tipo,
            "ativa": categoria.ativa
        }
        for categoria in categorias
    ]