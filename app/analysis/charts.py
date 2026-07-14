"""
Geracao de graficos (Plotly).

Os graficos sao gerados NO SERVIDOR e enviados ao navegador como JSON.
O navegador so precisa desenhar -- nao recebe os dados brutos do usuario.

Por que Plotly e nao Matplotlib? Plotly gera graficos INTERATIVOS (zoom, hover
com valores) e serializa nativamente para JSON, que e o que a web entende.
"""
from __future__ import annotations

import json
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.io as pio

from app.analysis.eda import TIPOS_NUMERICOS, colunas_por_tipo, matriz_correlacao
from app.profiling import TipoSemantico

MAX_HISTOGRAMAS = 4
CORES = px.colors.sequential.Teal


def _para_json(figura: Any) -> dict[str, Any]:
    """Serializa a figura. pio.to_json lida com os tipos do NumPy (que o json puro nao)."""
    return json.loads(pio.to_json(figura))


def _tema(figura: Any) -> Any:
    """Deixa o grafico transparente para casar com o tema escuro da pagina."""
    figura.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=20, t=50, b=40),
        height=320,
        font=dict(family="Inter, system-ui, sans-serif", size=12),
    )
    return figura


def gerar_graficos(
    df: pd.DataFrame, perfil: dict[str, TipoSemantico]
) -> list[dict[str, Any]]:
    """Histogramas das colunas numericas + mapa de calor das correlacoes."""
    graficos: list[dict[str, Any]] = []
    numericas = colunas_por_tipo(perfil, TIPOS_NUMERICOS)

    # 1) Distribuicao de cada variavel numerica (mostra a assimetria visualmente)
    for coluna in numericas[:MAX_HISTOGRAMAS]:
        serie = df[coluna].dropna()
        if serie.empty:
            continue
        figura = px.histogram(
            df, x=coluna, nbins=30, title=f"Distribuicao de {coluna}",
            color_discrete_sequence=["#2dd4bf"],
        )
        figura.add_vline(
            x=serie.median(), line_dash="dash", line_color="#f59e0b",
            annotation_text="mediana", annotation_position="top",
        )
        graficos.append({"titulo": f"Distribuicao de {coluna}", "figura": _para_json(_tema(figura))})

    # 2) Mapa de calor das correlacoes (so faz sentido com 2+ colunas numericas)
    if len(numericas) >= 2:
        matriz = matriz_correlacao(df, perfil).round(2)
        figura = px.imshow(
            matriz, text_auto=True, aspect="auto", zmin=-1, zmax=1,
            color_continuous_scale="RdBu_r", title="Mapa de correlacao",
        )
        graficos.append({"titulo": "Mapa de correlacao", "figura": _para_json(_tema(figura))})

    return graficos


def preview(df: pd.DataFrame, linhas: int = 10) -> dict[str, Any]:
    """Primeiras linhas do dataset, prontas para virar uma tabela HTML."""
    amostra = df.head(linhas).copy()

    # Datas e NaN nao sobrevivem ao JSON puro -> viram texto/None aqui.
    for coluna in amostra.columns:
        if pd.api.types.is_datetime64_any_dtype(amostra[coluna]):
            amostra[coluna] = amostra[coluna].dt.strftime("%d/%m/%Y")
    amostra = amostra.astype(object).where(pd.notna(amostra), None)

    return {
        "colunas": list(amostra.columns),
        "linhas": amostra.to_dict(orient="records"),
        "total_linhas": len(df),
    }
