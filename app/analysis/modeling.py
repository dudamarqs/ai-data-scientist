"""
Camada de Analise - Machine Learning (regressao).

Treina e compara varios modelos, sempre contra um BASELINE (modelo burro).
Usa Pipeline do scikit-learn: tudo que 'aprende' com os dados (mediana da
imputacao, categorias do one-hot) e aprendido SO NO TREINO -> sem data leakage.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from app.profiling import TipoSemantico

# Tipos que o modelo pode usar como feature (IDs e texto livre ficam de fora).
TIPOS_NUMERICOS = {TipoSemantico.NUMERICO, TipoSemantico.MOEDA}
TIPOS_CATEGORICOS = {TipoSemantico.CATEGORIA}


def selecionar_features(
    perfil: dict[str, TipoSemantico], alvo: str
) -> tuple[list[str], list[str]]:
    """Escolhe quais colunas viram features (numericas e categoricas).

    Identificadores (cliente_id) e texto livre sao DESCARTADOS de proposito:
    um ID nao tem poder preditivo -- usa-lo so ensina o modelo a decorar.
    """
    numericas = [
        c for c, t in perfil.items() if t in TIPOS_NUMERICOS and c != alvo
    ]
    categoricas = [
        c for c, t in perfil.items() if t in TIPOS_CATEGORICOS and c != alvo
    ]
    return numericas, categoricas


def construir_preprocessador(
    numericas: list[str], categoricas: list[str]
) -> ColumnTransformer:
    """Monta o pre-processamento: imputar numericas + one-hot nas categoricas.

    Vai DENTRO do Pipeline -> o `fit` roda so no treino (antileakage).
    """
    return ColumnTransformer(
        transformers=[
            ("num", SimpleImputer(strategy="median"), numericas),
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                categoricas,
            ),
        ]
    )


def criar_modelos() -> dict[str, object]:
    """Os concorrentes. O 'Baseline' sempre chuta a media -> regua minima."""
    return {
        "Baseline (chuta a media)": DummyRegressor(strategy="mean"),
        "Regressao Linear": LinearRegression(),
        "Random Forest": RandomForestRegressor(n_estimators=100, random_state=42),
        "Gradient Boosting": HistGradientBoostingRegressor(random_state=42),
    }


def avaliar_predicoes(y_real: np.ndarray, y_previsto: np.ndarray) -> dict[str, float]:
    """Calcula MAE, RMSE e R2."""
    return {
        "MAE": mean_absolute_error(y_real, y_previsto),
        "RMSE": float(np.sqrt(mean_squared_error(y_real, y_previsto))),
        "R2": r2_score(y_real, y_previsto),
    }


def treinar_e_comparar(
    df: pd.DataFrame,
    perfil: dict[str, TipoSemantico],
    alvo: str,
    *,
    test_size: float = 0.2,
    random_state: int = 42,
) -> pd.DataFrame:
    """Treina todos os modelos e devolve uma tabela comparativa, ordenada.

    Fluxo: separa X/y -> divide treino/teste -> para cada modelo, monta um
    Pipeline (preproc + modelo), treina SO no treino e avalia SO no teste.
    """
    numericas, categoricas = selecionar_features(perfil, alvo)
    X = df[numericas + categoricas]
    y = df[alvo]

    # A prova (teste) e separada ANTES de qualquer aprendizado. Sagrado.
    X_treino, X_teste, y_treino, y_teste = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )

    resultados = []
    for nome, modelo in criar_modelos().items():
        pipeline = Pipeline(
            [
                ("preproc", construir_preprocessador(numericas, categoricas)),
                ("modelo", modelo),
            ]
        )
        pipeline.fit(X_treino, y_treino)              # aprende SO no treino
        previsoes = pipeline.predict(X_teste)          # prevê no teste
        resultados.append({"modelo": nome, **avaliar_predicoes(y_teste, previsoes)})

    return (
        pd.DataFrame(resultados)
        .sort_values("R2", ascending=False)
        .reset_index(drop=True)
    )
