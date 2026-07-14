"""Testes da camada de interpretabilidade (SHAP)."""
import numpy as np
import pandas as pd

from app.interpret import (
    calcular_shap,
    explicar_previsao,
    importancia_global,
    treinar_para_explicar,
)
from app.profiling import TipoSemantico

PERFIL = {
    "preco": TipoSemantico.NUMERICO,
    "ruido": TipoSemantico.NUMERICO,
    "categoria": TipoSemantico.CATEGORIA,
    "quantidade": TipoSemantico.NUMERICO,
}


def _dados(n=200):
    rng = np.random.default_rng(0)
    df = pd.DataFrame(
        {
            "preco": rng.uniform(10, 1000, n),
            "ruido": rng.normal(0, 1, n),          # nao influencia nada
            "categoria": rng.choice(["A", "B"], n),
        }
    )
    # SO o preco determina a quantidade -> SHAP tem que apontar o preco
    df["quantidade"] = 20 - 0.01 * df["preco"] + rng.normal(0, 0.3, n)
    return df


def test_shap_aponta_a_feature_que_realmente_importa():
    df = _dados()
    pipeline, X_teste = treinar_para_explicar(df, PERFIL, alvo="quantidade")
    valores, nomes = calcular_shap(pipeline, X_teste)

    importancia = importancia_global(valores, nomes)
    # a feature mais importante tem que ser o preco (a unica que causa o alvo)
    assert "preco" in importancia.index[0]
    # o ruido (irrelevante) tem que importar bem menos que o preco
    assert importancia["num__ruido"] < importancia["num__preco"]


def test_explicacao_local_tem_uma_contribuicao_por_feature():
    df = _dados()
    pipeline, X_teste = treinar_para_explicar(df, PERFIL, alvo="quantidade")
    valores, nomes = calcular_shap(pipeline, X_teste)

    explicacao = explicar_previsao(valores, nomes, indice=0)
    assert len(explicacao) == len(nomes)
    # ordenada por magnitude (a mais influente primeiro)
    assert abs(explicacao.iloc[0]) >= abs(explicacao.iloc[-1])
