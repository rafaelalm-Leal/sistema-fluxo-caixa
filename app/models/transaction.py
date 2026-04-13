from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import String, Date, DateTime, ForeignKey, Numeric, Enum, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.enums import TipoMovimentacao


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tipo: Mapped[TipoMovimentacao] = mapped_column(
        Enum(TipoMovimentacao),
        nullable=False,
        index=True
    )
    descricao: Mapped[str] = mapped_column(String(150), nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    data_movimentacao: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    categoria_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id"),
        nullable=False,
        index=True
    )
    forma_pagamento: Mapped[str | None] = mapped_column(String(50), nullable=True)
    observacao: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )
    updated_by: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )