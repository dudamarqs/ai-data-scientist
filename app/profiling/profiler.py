"""
Camada de Profiling: descobre o TIPO SEMANTICO de cada coluna.

Tipo semantico = o SIGNIFICADO do dado (data, moeda, identificador...),
que e diferente do tipo fisico (int64, object). Usamos heuristicas:
regras praticas que combinam sinais (nome, valores, cardinalidade).

Heuristica != verdade absoluta: e um "chute educado" que acerta na maioria.
"""
from __future__ import annotations

import re
from enum import Enum

import pandas as pd


class TipoSemantico(str, Enum):
    """Lista fechada de tipos semanticos que sabemos detectar."""

    IDENTIFICADOR = "identificador"   # CEP, CPF, ID... nao se faz conta
    DATA = "data"
    MOEDA = "moeda"
    CATEGORIA = "categoria"           # poucos valores distintos, repetidos
    NUMERICO = "numerico"             # numero de verdade (faz conta)
    TEXTO = "texto"                   # texto livre, muitos valores unicos


# Pistas no NOME da coluna que denunciam um identificador.
PALAVRAS_IDENTIFICADOR = ("id", "cep", "cpf", "cnpj", "codigo", "cod")


def _taxa_conversao(serie: pd.Series, conversor) -> float:
    """Aplica um conversor com coerce e devolve a fracao que converteu (0..1)."""
    convertido = conversor(serie)
    return convertido.notna().mean()


def _parece_moeda(serie: pd.Series) -> bool:
    """True se a maioria dos valores tem simbolo de moeda (R$, $, EUR)."""
    amostra = serie.dropna().astype(str)
    if amostra.empty:
        return False
    return amostra.str.contains(r"R\$|\$|€", regex=True).mean() > 0.5


def detectar_tipo_semantico(
    serie: pd.Series,
    nome_coluna: str,
    *,
    limite_conversao: float = 0.8,
    limite_categoria: float = 0.5,
) -> TipoSemantico:
    """Descobre o tipo semantico de UMA coluna.

    A ordem das checagens vai do mais especifico ao mais generico.

    Args:
        serie: a coluna (ainda crua, como texto).
        nome_coluna: usado como pista (ex.: 'cep_loja').
        limite_conversao: fracao minima que precisa converter p/ valer o tipo.
        limite_categoria: razao de unicidade abaixo da qual e categoria.
    """
    nome = nome_coluna.lower()

    # 1) Pista pelo nome: identificadores nao viram numero de verdade.
    #    Comparamos por TOKEN (palavra inteira), nao por substring, para nao
    #    confundir 'quant-id-ade' com o token 'id'.
    tokens = re.split(r"[^a-z0-9]+", nome)
    if any(token in PALAVRAS_IDENTIFICADOR for token in tokens):
        return TipoSemantico.IDENTIFICADOR

    # 2) Moeda: tem simbolo (R$, $) -> tratar como dinheiro.
    if serie.dtype == object and _parece_moeda(serie):
        return TipoSemantico.MOEDA

    # 3) Numerico: a maioria converte para numero (e nao e data).
    taxa_num = _taxa_conversao(serie, lambda s: pd.to_numeric(s, errors="coerce"))
    if taxa_num >= limite_conversao:
        return TipoSemantico.NUMERICO

    # 4) Data: a maioria converte para datetime (formato BR: dia primeiro).
    taxa_data = _taxa_conversao(
        serie,
        lambda s: pd.to_datetime(s, errors="coerce", dayfirst=True, format="mixed"),
    )
    if taxa_data >= limite_conversao:
        return TipoSemantico.DATA

    # 5) Texto: categoria (poucos distintos) vs. texto livre (muitos distintos).
    razao_unicos = serie.nunique(dropna=True) / len(serie)
    if razao_unicos <= limite_categoria:
        return TipoSemantico.CATEGORIA
    return TipoSemantico.TEXTO


def perfilar(df: pd.DataFrame) -> dict[str, TipoSemantico]:
    """Detecta o tipo semantico de TODAS as colunas do DataFrame.

    Retorna um dicionario {nome_da_coluna: TipoSemantico}, que funciona como
    um 'schema sugerido' para as proximas etapas (limpeza/tipagem).
    """
    return {
        coluna: detectar_tipo_semantico(df[coluna], coluna) for coluna in df.columns
    }
