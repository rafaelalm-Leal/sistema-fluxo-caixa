from enum import Enum


class TipoMovimentacao(str, Enum):
    ENTRADA = "entrada"
    SAIDA = "saida"