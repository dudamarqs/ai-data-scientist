"""
Pipeline: amarra as camadas na ORDEM CORRETA.

    Ingestao -> Profiling -> Qualidade -> (pronto para Analise/ML/LLM)

Esta e a unica funcao que conhece todas as camadas. Cada camada continua
ignorando as outras (baixo acoplamento); a orquestracao mora aqui.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from app.ingestion import carregar_csv
from app.profiling import TipoSemantico, perfilar
from app.quality import converter_moeda_brl, remover_duplicatas


@dataclass(frozen=True)
class DatasetPreparado:
    """Resultado do pipeline: dados limpos + o schema semantico descoberto."""

    df: pd.DataFrame
    perfil: dict[str, TipoSemantico]
    duplicatas_removidas: int


def preparar(caminho: str | Path) -> DatasetPreparado:
    """Le, perfila e limpa um CSV, devolvendo-o pronto para analise."""
    bruto = carregar_csv(caminho)

    # 1) Profiling ANTES da limpeza: precisamos saber o que cada coluna E.
    perfil = perfilar(bruto)

    # 2) Identificadores devem ser texto (preserva zeros a esquerda: CEP 01310).
    identificadores = [
        coluna
        for coluna, tipo in perfil.items()
        if tipo == TipoSemantico.IDENTIFICADOR
    ]
    if identificadores:
        bruto = carregar_csv(caminho, dtype={c: str for c in identificadores})

    # 3) Qualidade: duplicatas + conversao de moeda para numero.
    limpo = remover_duplicatas(bruto)
    duplicatas = len(bruto) - len(limpo)

    for coluna, tipo in perfil.items():
        if tipo == TipoSemantico.MOEDA:
            limpo[coluna] = converter_moeda_brl(limpo[coluna])

    return DatasetPreparado(
        df=limpo, perfil=perfil, duplicatas_removidas=duplicatas
    )
