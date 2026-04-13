from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from app.enums import TipoMovimentacao


class TransactionCreate(BaseModel):
    tipo: TipoMovimentacao
    descricao: str
    valor: Decimal = Field(gt=0)
    data_movimentacao: date
    categoria_id: int
    forma_pagamento: str | None = None
    observacao: str | None = None
    created_by: int
    updated_by: int

class TransactionUpdate(BaseModel):
    tipo: TipoMovimentacao
    descricao: str
    valor: Decimal = Field(gt=0)
    data_movimentacao: date
    categoria_id: int
    forma_pagamento: str | None = None
    observacao: str | None = None
    updated_by: int

class TransactionResponse(BaseModel):
    id: int
    tipo: TipoMovimentacao
    descricao: str
    valor: Decimal
    data_movimentacao: date
    categoria_id: int
    forma_pagamento: str | None
    observacao: str | None
    created_by: int
    updated_by: int

    class Config:
        from_attributes = True