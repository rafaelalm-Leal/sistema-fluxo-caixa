from pydantic import BaseModel

from app.enums import TipoMovimentacao


class CategoryCreate(BaseModel):
    nome: str
    tipo: TipoMovimentacao


class CategoryResponse(BaseModel):
    id: int
    nome: str
    tipo: TipoMovimentacao
    ativa: bool

    class Config:
        from_attributes = True