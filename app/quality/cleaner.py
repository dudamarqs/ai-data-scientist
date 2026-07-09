"""
Camada de Qualidade de Dados (o "chef").

Responsabilidade: transformar o dado cru em dado limpo e confiavel.
Cada funcao faz UMA operacao de limpeza (SRP) e sempre devolve um NOVO
DataFrame/Serie -- nunca altera o original no lugar (imutabilidade -> menos bugs).
"""
from __future__ import annotations

import pandas as pd

ESTRATEGIAS_VALIDAS = {"mediana", "media"}


def remover_duplicatas(df: pd.DataFrame) -> pd.DataFrame:
    """Remove linhas totalmente duplicadas e reindexa.

    Retorna um NOVO DataFrame; o original nao e modificado.
    """
    return df.drop_duplicates().reset_index(drop=True)


def converter_moeda_brl(serie: pd.Series) -> pd.Series:
    """Converte texto de moeda BR ('R$ 3.499,90') para float (3499.90).

    Valores que nao representam um numero (ex.: 'indisponivel') viram NaN,
    para depois caírem na estrategia de imputacao.
    """
    limpo = (
        serie.astype(str)
        .str.replace(r"[R$\s]", "", regex=True)   # remove 'R$' e espacos
        .str.replace(".", "", regex=False)          # remove separador de milhar
        .str.replace(",", ".", regex=False)         # decimal BR (,) -> decimal (.)
    )
    # errors='coerce': o que nao virar numero vira NaN, sem quebrar.
    return pd.to_numeric(limpo, errors="coerce")


def preencher_faltantes(serie: pd.Series, estrategia: str = "mediana") -> pd.Series:
    """Preenche valores faltantes (NaN) de uma coluna numerica.

    Args:
        serie: coluna numerica com possiveis NaN.
        estrategia: 'mediana' (padrao, robusta a outliers) ou 'media'.

    Raises:
        ValueError: se a estrategia for desconhecida.
    """
    if estrategia not in ESTRATEGIAS_VALIDAS:
        raise ValueError(
            f"Estrategia invalida: '{estrategia}'. Use uma de {ESTRATEGIAS_VALIDAS}."
        )

    valor = serie.median() if estrategia == "mediana" else serie.mean()
    return serie.fillna(valor)
