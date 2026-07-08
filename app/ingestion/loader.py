"""
Camada de Ingestao.

Responsabilidade UNICA: trazer um arquivo para a memoria (DataFrame) de forma
integra e reproduzivel. Esta camada e AGNOSTICA ao conteudo -- ela nao sabe
o que e "preco" ou "data". Limpeza e tipagem semantica vem nos modulos 2 e 3.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd


class ErroDeIngestao(Exception):
    """Erro ao carregar um arquivo de dados.

    Encapsula os erros da biblioteca de leitura (pandas) atras de uma
    interface propria, para que o resto do sistema nao dependa do pandas.
    """


def carregar_csv(
    caminho: str | Path,
    *,
    separador: str = ",",
    encoding: str = "utf-8",
    **opcoes_leitura,
) -> pd.DataFrame:
    """Le um arquivo CSV e o devolve como DataFrame, sem limpar nada.

    Args:
        caminho: Caminho do arquivo .csv.
        separador: Delimitador de colunas (`,` padrao; use `;` p/ CSV do Excel BR).
        encoding: Codificacao de caracteres. Tenta utf-8 e cai p/ latin-1.
        **opcoes_leitura: Repassadas ao `pd.read_csv` (ex.: `dtype`, `parse_dates`).

    Returns:
        Um DataFrame com o conteudo cru (tipos ainda inferidos pelo pandas).

    Raises:
        ErroDeIngestao: se o arquivo nao existe, nao e .csv, esta vazio,
            ou nao pode ser lido.
    """
    caminho = Path(caminho)

    # 1) Validacoes de guarda: falhar cedo, com mensagem clara (fail-fast).
    if not caminho.exists():
        raise ErroDeIngestao(f"Arquivo nao encontrado: {caminho}")
    if not caminho.is_file():
        raise ErroDeIngestao(f"O caminho nao aponta para um arquivo: {caminho}")
    if caminho.suffix.lower() != ".csv":
        raise ErroDeIngestao(
            f"Extensao invalida '{caminho.suffix}'. Esperado um arquivo .csv."
        )

    # 2) Leitura, com fallback de encoding (comum em dados brasileiros).
    try:
        df = pd.read_csv(caminho, sep=separador, encoding=encoding, **opcoes_leitura)
    except UnicodeDecodeError:
        df = pd.read_csv(caminho, sep=separador, encoding="latin-1", **opcoes_leitura)
    except pd.errors.EmptyDataError as erro:
        raise ErroDeIngestao(f"Arquivo vazio (sem cabecalho): {caminho}") from erro
    except pd.errors.ParserError as erro:
        raise ErroDeIngestao(f"Falha ao interpretar o CSV: {caminho}") from erro

    # 3) Um CSV so com cabecalho e valido para o pandas, mas inutil para nos.
    if df.empty:
        raise ErroDeIngestao(f"Arquivo sem linhas de dados: {caminho}")

    return df
