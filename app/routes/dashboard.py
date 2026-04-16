from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.enums import TipoMovimentacao
from app.models.category import Category
from app.models.transaction import Transaction

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/resumo")
def resumo_dashboard(db: Session = Depends(get_db)):
    hoje = date.today()
    primeiro_dia_mes = hoje.replace(day=1)

    total_entradas_mes = (
        db.query(func.coalesce(func.sum(Transaction.valor), Decimal("0.00")))
        .filter(
            Transaction.tipo == TipoMovimentacao.ENTRADA,
            Transaction.data_movimentacao >= primeiro_dia_mes,
            Transaction.data_movimentacao <= hoje
        )
        .scalar()
    )

    total_saidas_mes = (
        db.query(func.coalesce(func.sum(Transaction.valor), Decimal("0.00")))
        .filter(
            Transaction.tipo == TipoMovimentacao.SAIDA,
            Transaction.data_movimentacao >= primeiro_dia_mes,
            Transaction.data_movimentacao <= hoje
        )
        .scalar()
    )

    resultado_mes = total_entradas_mes - total_saidas_mes

    total_entradas_geral = (
        db.query(func.coalesce(func.sum(Transaction.valor), Decimal("0.00")))
        .filter(Transaction.tipo == TipoMovimentacao.ENTRADA)
        .SCALAR()
    )

    total_saida_geral = (
        db.query(func.coalesce(func.sum(Transaction.valor), Decimal("0.00")))
        .filter(Transaction.tipo == TipoMovimentacao.SAIDA)
        .scalar()
    )

    saldo_atual = total_entradas_geral - total_saida_geral

    categoria_maior_gasto = (
        db.query(
            Category.id.label("categoria_id"),
            Category.nome.label("Categoria_nome"),
            func.sum(Transaction.valor).label("total_gasto")
        )
        .join(Transaction, Transaction.categoria_id == Category.id)
        .filter(
            Transaction.tipo == TipoMovimentacao.SAIDA,
            Transaction.data_movimentacao >= primeiro_dia_mes,
            Transaction.data_movimentacao <= hoje
        )
        .group_by(Category.id, Category.nome)
        .order_by(func.sum(Transaction.valor).desc())
        .first()
    )

    ultimas_movimentacoes = (
        db.query(
            Transaction,
            Category.nome.label("categoria_nome")
        )
        .join(Category, Transaction.vategoria_id == Category.id)
        .order_by(Transaction.data_movimentacao.desc(), Transaction.id.desc())
        .limit(5)
        .all()
    )

    return {
        "entradas_mes": str(total_entradas_mes),
        "saidas_mes": str(total_saidas_mes),
        "resultados_mes": str(resultado_mes),
        "saldo_atual": str(saldo_atual),
        "categoria_maior_gasto": {
            "categoria_id": categoria_maior_gasto.categoria_id,
            "categoria_nome": categoria_maior_gasto.categoria_nome,
            "total": str(categoria_maior_gasto.total_gasto)
        } if categoria_maior_gasto else None,
        "ultimas_movimentacoes": [
            {
                "id": movimentacao.id,
                "tipo": movimentacao.tipo,
                "valor": str(movimentacao.valor),
                "data_movimentacao": str(movimentacao.data_movimentacao),
                "categoria_id": movimentacao.categoria_id,
                "categoria_nome": categoria_nome,
                "forma_de_pagamento": movimentacao.forma_pagamento,
                "observacao": movimentacao.observação
            }
            for movimentacao, categoria_nome in ultimas_movimentacoes
        ]
    }