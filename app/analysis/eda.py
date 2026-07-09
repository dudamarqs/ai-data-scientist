"""
Camada de Analise - EDA (Exploratory Data Analysis).

Extrai conhecimento de dados JA LIMPOS e TIPADOS. Usa o perfil semantico
(vindo do profiling) para analisar apenas as colunas em que a estatistica
faz sentido -- nunca calcula media de um identificador (CEP/ID).

Pre-condicao: as colunas numericas/moeda ja devem estar convertidas para
numero (isso e trabalho da camada de qualidade, que roda antes).
"""
from __future__ import annotations

import pandas as pd

from app.profiling import TipoSemantico

# Tipos semanticos em que calcular estatistica numerica faz sentido.
TIPOS_NUMERICOS = {TipoSemantico.NUMERICO, TipoSemantico.MOEDA}


def colunas_por_tipo(
    perfil: dict[str, TipoSemantico], tipos: set[TipoSemantico]
) -> list[str]:
    """Lista as colunas cujo tipo semantico esta no conjunto pedido."""
    return [coluna for coluna, tipo in perfil.items() if tipo in tipos]


def estatisticas_descritivas(
    df: pd.DataFrame, perfil: dict[str, TipoSemantico]
) -> pd.DataFrame:
    """Estatisticas descritivas SO das colunas numericas/moeda.

    Acrescenta 'mediana' e 'assimetria' (skew) ao describe padrao, porque
    sao essenciais para entender outliers e a forma da distribuicao.
    """
    colunas = colunas_por_tipo(perfil, TIPOS_NUMERICOS)
    if not colunas:
        return pd.DataFrame()

    resumo = df[colunas].describe().T          # .T = colunas viram linhas
    resumo["mediana"] = df[colunas].median()
    resumo["assimetria"] = df[colunas].skew()
    return resumo


def matriz_correlacao(
    df: pd.DataFrame,
    perfil: dict[str, TipoSemantico],
    metodo: str = "pearson",
) -> pd.DataFrame:
    """Matriz de correlacao entre as colunas numericas.

    metodo: 'pearson' (relacao linear) ou 'spearman' (relacao monotonica).
    Lembre-se: correlacao NAO e causalidade.
    """
    colunas = colunas_por_tipo(perfil, TIPOS_NUMERICOS)
    return df[colunas].corr(method=metodo)


def resumo_categorico(
    df: pd.DataFrame, perfil: dict[str, TipoSemantico]
) -> dict[str, pd.Series]:
    """Contagem de valores de cada coluna categorica (o 'menu' e sua frequencia)."""
    colunas = colunas_por_tipo(perfil, {TipoSemantico.CATEGORIA})
    return {coluna: df[coluna].value_counts() for coluna in colunas}
