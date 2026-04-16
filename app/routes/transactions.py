from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, aliased

from app.database import get_db
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.transaction import TransactionCreate, TransactionUpdate
from app.enums import TipoMovimentacao

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.post("")
def criar_movimentacao(transaction: TransactionCreate, db: Session = Depends(get_db)):
    categoria = db.query(Category).filter(Category.id == transaction.categoria_id).first()

    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")

    if categoria.tipo != transaction.tipo:
        raise HTTPException(
            status_code=400,
            detail="O tipo da movimentação não é compatível com o tipo da categoria"
        )

    usuario_criador = db.query(User).filter(User.id == transaction.created_by).first()
    if not usuario_criador:
        raise HTTPException(status_code=404, detail="Usuário criador não encontrado")

    usuario_editor = db.query(User).filter(User.id == transaction.updated_by).first()
    if not usuario_editor:
        raise HTTPException(status_code=404, detail="Usuário editor não encontrado")

    nova_movimentacao = Transaction(
        tipo=transaction.tipo,
        descricao=transaction.descricao,
        valor=transaction.valor,
        data_movimentacao=transaction.data_movimentacao,
        categoria_id=transaction.categoria_id,
        forma_pagamento=transaction.forma_pagamento,
        observacao=transaction.observacao,
        created_by=transaction.created_by,
        updated_by=transaction.updated_by,
    )

    db.add(nova_movimentacao)
    db.commit()
    db.refresh(nova_movimentacao)

    return {
        "mensagem": "Movimentação criada com sucesso",
        "movimentacao": {
            "id": nova_movimentacao.id,
            "tipo": nova_movimentacao.tipo,
            "descricao": nova_movimentacao.descricao,
            "valor": str(nova_movimentacao.valor),
            "data_movimentacao": str(nova_movimentacao.data_movimentacao),
            "categoria_id": nova_movimentacao.categoria_id,
            "forma_pagamento": nova_movimentacao.forma_pagamento,
            "observacao": nova_movimentacao.observacao,
            "created_by": nova_movimentacao.created_by,
            "updated_by": nova_movimentacao.updated_by,
        }
    }


@router.get("")
def listar_movimentacoes(db: Session = Depends(get_db)):
    usuario_criador = aliased(User)
    usuario_editor = aliased(User)

    movimentacoes = (
        db.query(
            Transaction,
            Category.nome.label("categoria_nome"),
            usuario_criador.nome.label("criado_por_nome"),
            usuario_editor.nome.label("atualizado_por_nome")
        )
        .join(Category, Transaction.categoria_id == Category.id)
        .join(usuario_criador, Transaction.created_by == usuario_criador.id)
        .join(usuario_editor, Transaction.updated_by == usuario_editor.id)
        .order_by(Transaction.data_movimentacao.desc(), Transaction.id.desc())
        .all()
    )

    return [
        {
            "id": movimentacao.id,
            "tipo": movimentacao.tipo,
            "descricao": movimentacao.descricao,
            "valor": str(movimentacao.valor),
            "data_movimentacao": str(movimentacao.data_movimentacao),
            "categoria_id": movimentacao.categoria_id,
            "categoria_nome": categoria_nome,
            "forma_pagamento": movimentacao.forma_pagamento,
            "observacao": movimentacao.observacao,
            "created_by": movimentacao.created_by,
            "criado_por_nome": criado_por_nome,
            "updated_by": movimentacao.updated_by,
            "atualizado_por_nome": atualizado_por_nome,
        }
        for movimentacao, categoria_nome, criado_por_nome, atualizado_por_nome in movimentacoes
    ]

@router.get("/historico")
def historico_movimentacoes(
    data_inicio: date | None = Query(default=None),
    data_fim: date | None = Query(default=None),
    tipo: str | None = Query(default=None),
    categoria_id: int | None = Query(default=None),
    db: Session = Depends(get_db)
):
    usuario_criador = aliased(User)
    usuario_editor = aliased(User)

    query = (
        db.query(
            Transaction,
            Category.nome.label("categoria_nome"),
            usuario_criador.nome.label("criado_por_nome"),
            usuario_editor.nome.label("editado_por_nome")
        )
        .join(Category, Transaction.categoria_id == Category.id)
        .join(usuario_criador, Transaction.created_by == usuario_criador.id)
        .join(usuario_editor, Transaction.updated_by == usuario_editor.id)
    )

    if data_inicio:
        query = query.filter(Transaction.data_movimentacao >= data_inicio)

    if data_fim:
        query = query.filter(Transaction.data_movimentacao <= data_fim)

    if tipo:
        query = query.filter(Transaction.tipo == tipo)

    if categoria_id:
        query = query.filter(Transaction.categoria_id == categoria_id)

    resultados = query.order_by(
        Transaction.data_movimentacao.desc(),
        Transaction.id.desc()
    ).all()

    historico_agrupado = {}

    for movimentacao, categoria_nome, criado_por_nome, atualizado_por_nome in resultados:
        data_str = str(movimentacao.data_movimentacao)

        if data_str not in historico_agrupado:
            historico_agrupado[data_str] = {
                "data": data_str,
                "entradas_dia": Decimal("0.00"),
                "saidas_dia": Decimal("0.00"),
                "saldo_dia": Decimal("0.00"),
                "movimentacoes": []
            }

        if movimentacao.tipo == TipoMovimentacao.ENTRADA:
            historico_agrupado[data_str]["entradas_dia"] += movimentacao.valor
            historico_agrupado[data_str]["saldo_dia"] += movimentacao.valor
        else:
            historico_agrupado[data_str]["saidas_dia"] += movimentacao.valor
            historico_agrupado[data_str]["saldo_dia"] -= movimentacao.valor

        historico_agrupado[data_str]["movimentacoes"].append({
            "id": movimentacao.id,
            "tipo": movimentacao.tipo,
            "descricao": movimentacao.descricao,
            "valor": str(movimentacao.valor),
            "categoria_id": movimentacao.categoria_id,
            "categoria_nome": categoria_nome,
            "forma_pagamento": movimentacao.forma_pagamento,
            "observacao": movimentacao.observacao,
            "created_by": movimentacao.created_by,
            "criado_por_nome": criado_por_nome,
            "updated_by": movimentacao.updated_by,
            "atualizado_por_nome": atualizado_por_nome
        })

    resposta = []

    for grupo in historico_agrupado.values():
        resposta.append({
            "data": grupo["data"],
            "entradas_dia": str(grupo["entradas_dia"]),
            "saidas_dia": str(grupo["saidas_dia"]),
            "saldo_dia": str(grupo["saldo_dia"]),
            "movimentacoes": grupo["movimentacoes"]
        })

    return resposta

@router.put("/{transaction_id}")
def editar_movimentacao(
    transaction_id: int,
    transaction_data: TransactionUpdate,
    db: Session = Depends(get_db)
):
    movimentacao = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id)
        .first()
    )

    if not movimentacao:
        raise HTTPException(status_code=404, detail="Movimentação não encontrada")

    categoria = (
        db.query(Category)
        .filter(Category.id == transaction_data.categoria_id)
        .first()
    )

    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")

    if categoria.tipo != transaction_data.tipo:
        raise HTTPException(
            status_code=400,
            detail="O tipo da movimentação não é compatível com o tipo da categoria"
        )

    usuario_editor = (
        db.query(User)
        .filter(User.id == transaction_data.updated_by)
        .first()
    )

    if not usuario_editor:
        raise HTTPException(status_code=404, detail="Usuário editor não encontrado")

    movimentacao.tipo = transaction_data.tipo
    movimentacao.descricao = transaction_data.descricao
    movimentacao.valor = transaction_data.valor
    movimentacao.data_movimentacao = transaction_data.data_movimentacao
    movimentacao.categoria_id = transaction_data.categoria_id
    movimentacao.forma_pagamento = transaction_data.forma_pagamento
    movimentacao.observacao = transaction_data.observacao
    movimentacao.updated_by = transaction_data.updated_by

    db.commit()
    db.refresh(movimentacao)

    return {
        "mensagem": "Movimentação atualizada com sucesso",
        "movimentacao": {
            "id": movimentacao.id,
            "tipo": movimentacao.tipo,
            "descricao": movimentacao.descricao,
            "valor": str(movimentacao.valor),
            "data_movimentacao": str(movimentacao.data_movimentacao),
            "categoria_id": movimentacao.categoria_id,
            "forma_pagamento": movimentacao.forma_pagamento,
            "observacao": movimentacao.observacao,
            "created_by": movimentacao.created_by,
            "updated_by": movimentacao.updated_by
        }
    }