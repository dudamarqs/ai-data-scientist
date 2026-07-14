"""
Camada de Interpretabilidade (SHAP).

Abre a caixa-preta: mostra QUAIS variaveis o modelo usou e QUANTO cada uma
pesou -- tanto no geral (global) quanto numa previsao especifica (local).

Baseado nos valores de Shapley (teoria dos jogos, Nobel 1953): cada feature e
um 'jogador' e a previsao e o 'premio' a ser dividido de forma justa.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import shap
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from app.analysis.modeling import construir_preprocessador, selecionar_features
from app.profiling import TipoSemantico


def treinar_para_explicar(
    df: pd.DataFrame,
    perfil: dict[str, TipoSemantico],
    alvo: str,
    *,
    test_size: float = 0.2,
    random_state: int = 42,
) -> tuple[Pipeline, pd.DataFrame]:
    """Treina um modelo de arvore (explicavel via TreeExplainer) e devolve o teste."""
    numericas, categoricas = selecionar_features(perfil, alvo)
    X = df[numericas + categoricas]
    y = df[alvo]

    X_treino, X_teste, y_treino, _ = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )

    pipeline = Pipeline(
        [
            ("preproc", construir_preprocessador(numericas, categoricas)),
            ("modelo", RandomForestRegressor(n_estimators=100, random_state=random_state)),
        ]
    )
    pipeline.fit(X_treino, y_treino)
    return pipeline, X_teste


def calcular_shap(
    pipeline: Pipeline, X: pd.DataFrame
) -> tuple[np.ndarray, np.ndarray]:
    """Calcula os valores SHAP para cada linha e cada feature.

    Retorna (matriz_shap, nomes_das_features). A matriz tem uma linha por
    amostra e uma coluna por feature (ja pos one-hot).
    """
    preproc = pipeline.named_steps["preproc"]
    modelo = pipeline.named_steps["modelo"]

    X_transformado = preproc.transform(X)
    nomes = preproc.get_feature_names_out()

    explainer = shap.TreeExplainer(modelo)
    valores = explainer.shap_values(X_transformado)
    return valores, nomes


def importancia_global(valores_shap: np.ndarray, nomes: np.ndarray) -> pd.Series:
    """Importancia GERAL: media do |SHAP| de cada feature, do maior p/ o menor.

    Responde: 'quais variaveis o modelo mais usa para decidir?'
    """
    media_absoluta = np.abs(valores_shap).mean(axis=0)
    return pd.Series(media_absoluta, index=nomes).sort_values(ascending=False)


def explicar_previsao(
    valores_shap: np.ndarray, nomes: np.ndarray, indice: int
) -> pd.Series:
    """Explicacao LOCAL: por que ESTA linha recebeu esta previsao.

    Valor positivo = empurrou a previsao para CIMA; negativo = para BAIXO.
    """
    contribuicoes = pd.Series(valores_shap[indice], index=nomes)
    return contribuicoes.reindex(contribuicoes.abs().sort_values(ascending=False).index)
