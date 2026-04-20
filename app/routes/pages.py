from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session, aliased

from app.database import get_db
from app.enums import TipoMovimentacao
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.user import User
from app.security import gerar_hash_senha
from app.auth import buscar_usuario_logado, exigir_admin, exigir_usuario_logado
from app.security import gerar_hash_senha, verificar_senha

router = APIRouter(tags=["Pages"])
templates = Jinja2Templates(directory="app/templates")


def formatar_moeda(valor: Decimal) -> str:
    return f"R$ {valor:.2f}"

@router.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "erro": ""
        }
    )


@router.post("/login")
def login_submit(
    request: Request,
    email: str = Form(...),
    senha: str = Form(...),
    db: Session = Depends(get_db)
):
    email = email.strip().lower()

    usuario = (
        db.query(User)
        .filter(User.email == email, User.ativo == True)
        .first()
    )

    if not usuario or not verificar_senha(senha, usuario.senha_hash):
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "erro": "Email ou senha inválidos"
            },
            status_code=400
        )

    request.session["user_id"] = usuario.id

    return RedirectResponse(url="/dashboard", status_code=303)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


@router.get("/dashboard")
def dashboard_page(request: Request, db: Session = Depends(get_db)):
    usuario_logado = exigir_usuario_logado(request, db)
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

    total_saida_mes = (
        db.query(func.coalesce(func.sum(Transaction.valor), Decimal("0.00")))
        .filter(
            Transaction.tipo == TipoMovimentacao.SAIDA,
            Transaction.data_movimentacao >= primeiro_dia_mes,
            Transaction.data_movimentacao <= hoje
        )
        .scalar()
    )

    resultado_mes = total_entradas_mes - total_saida_mes

    total_entradas_geral = (
        db.query(func.coalesce(func.sum(Transaction.valor), Decimal("0.00")))
        .filter(Transaction.tipo == TipoMovimentacao.ENTRADA)
        .scalar()
    )

    total_saidas_geral = (
        db.query(func.coalesce(func.sum(Transaction.valor), Decimal("0.00")))
        .filter(Transaction.tipo == TipoMovimentacao.SAIDA)
        .scalar()
    )

    saldo_atual = total_entradas_geral - total_saidas_geral

    categoria_maior_gasto = (
        db.query(
            Category.id,
            Category.nome,
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
        .join(Category, Transaction.categoria_id == Category.id)
        .order_by(Transaction.data_movimentacao.desc(), Transaction.id.desc())
        .limit(5)
        .all()
    )

    categoria_resumo = None
    if categoria_maior_gasto:
        categoria_resumo = {
            "id": categoria_maior_gasto[0],
            "nome": categoria_maior_gasto[1],
            "total": formatar_moeda(categoria_maior_gasto[2])
        }

    ultimas_movimentacoes_formatadas = []
    for movimentacao, categoria_nome in ultimas_movimentacoes:
        ultimas_movimentacoes_formatadas.append({
            "id": movimentacao.id,
            "tipo": movimentacao.tipo.value,
            "descricao": movimentacao.descricao,
            "valor": formatar_moeda(movimentacao.valor),
            "data_movimentacao": str(movimentacao.data_movimentacao),
            "categoria_nome": categoria_nome,
            "forma_de_pagamento": movimentacao.forma_pagamento or "-",
            "observacao": movimentacao.observacao or "-"
        })

    return templates.TemplateResponse(
    request=request,
    name="dashboard.html",
    context={
        "entradas_mes": formatar_moeda(total_entradas_mes),
        "saidas_mes": formatar_moeda(total_saida_mes),
        "resultado_mes": formatar_moeda(resultado_mes),
        "saldo_atual": formatar_moeda(saldo_atual),
        "categoria_maior_gasto": categoria_resumo,
        "ultimas_movimentacoes": ultimas_movimentacoes_formatadas
    }
)

@router.get("/movimentacoes/nova")
def nova_movimentacao_page(request: Request, db: Session = Depends(get_db)):
    usuario_logado = exigir_usuario_logado(request, db)
    categorias = (
        db.query(Category)
        .filter(Category.ativa == True)
        .order_by(Category.tipo.asc(), Category.nome.asc())
        .all()
    )

    usuarios = (
        db.query(User)
        .filter(User.ativo == True)
        .order_by(User.nome.asc())
        .all()
    )

    categorias_formatadas = [
        {
            "id": categoria.id,
            "nome": categoria.nome,
            "tipo": categoria.tipo.value
        }
        for categoria in categorias
    ]

    usuarios_formatados = [
        {
            "id": usuario.id,
            "nome": usuario.nome
        }
        for usuario in usuarios
    ]

    return templates.TemplateResponse(
        request=request,
        name="nova_movimentacao.html",
        context={
            "categorias": categorias_formatadas,
            "usuarios": usuarios_formatados
        }
    )


@router.post("/movimentacoes/nova")
def salvar_movimentacao_page(
    tipo: TipoMovimentacao = Form(...),
    descricao: str = Form(...),
    valor: Decimal = Form(...),
    data_movimentacao: date = Form(...),
    categoria_id: int = Form(...),
    forma_pagamento: str | None = Form(None),
    observacao: str | None = Form(None),
    usuario_id: int = Form(...),
    db: Session = Depends(get_db)
):
    descricao = descricao.strip()

    if not descricao:
        raise HTTPException(status_code=400, detail="A descrição é obrigatória")

    if valor <= 0:
        raise HTTPException(status_code=400, detail="O valor deve ser maior que zero")

    categoria = (
        db.query(Category)
        .filter(Category.id == categoria_id)
        .first()
    )

    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")

    if not categoria.ativa:
        raise HTTPException(status_code=400, detail="A categoria está inativa")

    if categoria.tipo != tipo:
        raise HTTPException(
            status_code=400,
            detail="O tipo da movimentação não é compatível com o tipo da categoria"
        )

    usuario = (
        db.query(User)
        .filter(User.id == usuario_id, User.ativo == True)
        .first()
    )

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    nova_movimentacao = Transaction(
        tipo=tipo,
        descricao=descricao,
        valor=valor,
        data_movimentacao=data_movimentacao,
        categoria_id=categoria_id,
        forma_pagamento=forma_pagamento or None,
        observacao=observacao or None,
        created_by=usuario_id,
        updated_by=usuario_id
    )

    db.add(nova_movimentacao)
    db.commit()

    return RedirectResponse(url="/dashboard", status_code=303)

@router.get("/movimentacoes/historico")
def historico_movimentacoes_page(
    request: Request,
    data_inicio: date | None = Query(default=None),
    data_fim: date | None = Query(default=None),
    tipo: TipoMovimentacao | None = Query(default=None),
    categoria_id: int | None = Query(default=None),
    db: Session = Depends(get_db)
):
    usuario_logado = exigir_usuario_logado(request, db)
    usuario_criador = aliased(User)
    usuario_editor = aliased(User)

    categorias = (
        db.query(Category)
        .filter(Category.ativa == True)
        .order_by(Category.tipo.asc(), Category.nome.asc())
        .all()
    )

    query = (
        db.query(
            Transaction,
            Category.nome.label("categoria_nome"),
            usuario_criador.nome.label("criado_por_nome"),
            usuario_editor.nome.label("atualizado_por_nome")
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
            "tipo": movimentacao.tipo.value,
            "descricao": movimentacao.descricao,
            "valor": formatar_moeda(movimentacao.valor),
            "categoria_nome": categoria_nome,
            "forma_pagamento": movimentacao.forma_pagamento or "-",
            "observacao": movimentacao.observacao or "-",
            "criado_por_nome": criado_por_nome,
            "atualizado_por_nome": atualizado_por_nome
        })

    historico_formatado = []

    for grupo in historico_agrupado.values():
        historico_formatado.append({
            "data": grupo["data"],
            "entradas_dia": formatar_moeda(grupo["entradas_dia"]),
            "saidas_dia": formatar_moeda(grupo["saidas_dia"]),
            "saldo_dia": formatar_moeda(grupo["saldo_dia"]),
            "movimentacoes": grupo["movimentacoes"]
        })

    categorias_formatadas = [
        {
            "id": categoria.id,
            "nome": categoria.nome,
            "tipo": categoria.tipo.value
        }
        for categoria in categorias
    ]

    return templates.TemplateResponse(
        request=request,
        name="historico_movimentacoes.html",
        context={
            "historico": historico_formatado,
            "categorias": categorias_formatadas,
            "filtros": {
                "data_inicio": str(data_inicio) if data_inicio else "",
                "data_fim": str(data_fim) if data_fim else "",
                "tipo": tipo.value if tipo else "",
                "categoria_id": categoria_id if categoria_id else ""
            }
        }
    )

@router.get("/movimentacoes/editar/{movimentacao_id}")
def editar_movimentacao_page(
    movimentacao_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    usuario_logado = exigir_usuario_logado(request, db)
    movimentacao = (
        db.query(Transaction)
        .filter(Transaction.id == movimentacao_id)
        .first()
    )

    if not movimentacao:
        raise HTTPException(status_code=404, detail="Movimentação não encontrada")

    categorias = (
        db.query(Category)
        .filter(Category.ativa == True)
        .order_by(Category.tipo.asc(), Category.nome.asc())
        .all()
    )

    usuarios = (
        db.query(User)
        .filter(User.ativo == True)
        .order_by(User.nome.asc())
        .all()
    )

    categorias_formatadas = [
        {
            "id": categoria.id,
            "nome": categoria.nome,
            "tipo": categoria.tipo.value
        }
        for categoria in categorias
    ]

    usuarios_formatados = [
        {
            "id": usuario.id,
            "nome": usuario.nome
        }
        for usuario in usuarios
    ]

    movimentacao_formatada = {
        "id": movimentacao.id,
        "tipo": movimentacao.tipo.value,
        "descricao": movimentacao.descricao,
        "valor": str(movimentacao.valor),
        "data_movimentacao": str(movimentacao.data_movimentacao),
        "categoria_id": movimentacao.categoria_id,
        "forma_pagamento": movimentacao.forma_pagamento or "",
        "observacao": movimentacao.observacao or "",
        "updated_by": movimentacao.updated_by
    }

    return templates.TemplateResponse(
        request=request,
        name="editar_movimentacao.html",
        context={
            "movimentacao": movimentacao_formatada,
            "categorias": categorias_formatadas,
            "usuarios": usuarios_formatados
        }
    )


@router.post("/movimentacoes/editar/{movimentacao_id}")
def salvar_edicao_movimentacao_page(
    movimentacao_id: int,
    tipo: TipoMovimentacao = Form(...),
    descricao: str = Form(...),
    valor: Decimal = Form(...),
    data_movimentacao: date = Form(...),
    categoria_id: int = Form(...),
    forma_pagamento: str | None = Form(None),
    observacao: str | None = Form(None),
    usuario_id: int = Form(...),
    db: Session = Depends(get_db)
):
    movimentacao = (
        db.query(Transaction)
        .filter(Transaction.id == movimentacao_id)
        .first()
    )

    if not movimentacao:
        raise HTTPException(status_code=404, detail="Movimentação não encontrada")

    descricao = descricao.strip()

    if not descricao:
        raise HTTPException(status_code=400, detail="A descrição é obrigatória")

    if valor <= 0:
        raise HTTPException(status_code=400, detail="O valor deve ser maior que zero")

    categoria = (
        db.query(Category)
        .filter(Category.id == categoria_id)
        .first()
    )

    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")

    if not categoria.ativa:
        raise HTTPException(status_code=400, detail="A categoria está inativa")

    if categoria.tipo != tipo:
        raise HTTPException(
            status_code=400,
            detail="O tipo da movimentação não é compatível com o tipo da categoria"
        )

    usuario = (
        db.query(User)
        .filter(User.id == usuario_id, User.ativo == True)
        .first()
    )

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    movimentacao.tipo = tipo
    movimentacao.descricao = descricao
    movimentacao.valor = valor
    movimentacao.data_movimentacao = data_movimentacao
    movimentacao.categoria_id = categoria_id
    movimentacao.forma_pagamento = forma_pagamento or None
    movimentacao.observacao = observacao or None
    movimentacao.updated_by = usuario_id

    db.commit()

    return RedirectResponse(url="/movimentacoes/historico", status_code=303)

@router.get("/categorias")
def categorias_page(request: Request, db: Session = Depends(get_db)):
    usuario_admin = exigir_admin(request, db)
    categorias = (
        db.query(Category)
        .order_by(Category.tipo.asc(), Category.nome.asc())
        .all()
    )

    categorias_formatadas = [
        {
            "id": categoria.id,
            "nome": categoria.nome,
            "tipo": categoria.tipo.value,
            "ativa": categoria.ativa
        }
        for categoria in categorias
    ]

    return templates.TemplateResponse(
        request=request,
        name="categorias.html",
        context={
            "categorias": categorias_formatadas
        }
    )


@router.post("/categorias/nova")
def criar_categoria_page(
    request: Request,
    nome: str = Form(...),
    tipo: TipoMovimentacao = Form(...),
    db: Session = Depends(get_db)
):
    usuario_admin = exigir_admin(request, db)
    nome = nome.strip()

    if not nome:
        raise HTTPException(status_code=400, detail="O nome da categoria é obrigatório")

    categoria_existente = (
        db.query(Category)
        .filter(Category.nome == nome, Category.tipo == tipo)
        .first()
    )

    if categoria_existente:
        raise HTTPException(
            status_code=400,
            detail="Já existe uma categoria com esse nome e tipo"
        )

    nova_categoria = Category(
        nome=nome,
        tipo=tipo,
        ativa=True
    )

    db.add(nova_categoria)
    db.commit()

    return RedirectResponse(url="/categorias", status_code=303)


@router.post("/categorias/{categoria_id}/alternar-status")
def alternar_status_categoria_page(
    request: Request,
    categoria_id: int,
    db: Session = Depends(get_db)
):
    usuario_admin = exigir_admin(request, db)
    categoria = (
        db.query(Category)
        .filter(Category.id == categoria_id)
        .first()
    )

    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")

    categoria.ativa = not categoria.ativa
    db.commit()

    return RedirectResponse(url="/categorias", status_code=303)

@router.get("/usuarios")
def usuarios_page(request: Request, db: Session = Depends(get_db)):
    usuario_admin = exigir_admin(request, db)
    usuarios = (
        db.query(User)
        .order_by(User.nome.asc())
        .all()
    )

    usuarios_formatados = [
        {
            "id": usuario.id,
            "nome": usuario.nome,
            "email": usuario.email,
            "is_admin": usuario.is_admin,
            "ativo": usuario.ativo
        }
        for usuario in usuarios
    ]

    return templates.TemplateResponse(
        request=request,
        name="usuarios.html",
        context={
            "usuarios": usuarios_formatados
        }
    )


@router.post("/usuarios/novo")
def criar_usuario_page(
    request: Request,
    nome: str = Form(...),
    email: str = Form(...),
    senha: str = Form(...),
    is_admin: str | None = Form(None),
    db: Session = Depends(get_db)
):
    usuario_admin = exigir_admin(request, db)
    nome = nome.strip()
    email = email.strip().lower()

    if not nome:
        raise HTTPException(status_code=400, detail="O nome é obrigatório")

    if not email:
        raise HTTPException(status_code=400, detail="O email é obrigatório")

    if not senha.strip():
        raise HTTPException(status_code=400, detail="A senha é obrigatória")

    usuario_existente = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if usuario_existente:
        raise HTTPException(status_code=400, detail="Já existe um usuário com esse email")

    novo_usuario = User(
        nome=nome,
        email=email,
        senha_hash=gerar_hash_senha(senha),
        is_admin=bool(is_admin),
        ativo=True
    )

    db.add(novo_usuario)
    db.commit()

    return RedirectResponse(url="/usuarios", status_code=303)


@router.post("/usuarios/{usuario_id}/alternar-status")
def alternar_status_usuario_page(
    request: Request,
    usuario_id: int,
    db: Session = Depends(get_db)
):
    usuario_admin = exigir_admin(request, db)
    usuario = (
        db.query(User)
        .filter(User.id == usuario_id)
        .first()
    )

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    usuario.ativo = not usuario.ativo
    db.commit()

    return RedirectResponse(url="/usuarios", status_code=303)