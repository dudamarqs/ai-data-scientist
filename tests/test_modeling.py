"""Testes da camada de modelagem (ML)."""
import numpy as np
import pandas as pd

from app.analysis.modeling import (
    avaliar_predicoes,
    selecionar_features,
    treinar_e_comparar,
)
from app.profiling import TipoSemantico

PERFIL = {
    "preco": TipoSemantico.MOEDA,
    "avaliacao": TipoSemantico.NUMERICO,
    "categoria": TipoSemantico.CATEGORIA,
    "cliente_id": TipoSemantico.IDENTIFICADOR,
    "quantidade": TipoSemantico.NUMERICO,
}


def test_selecionar_features_descarta_identificador_e_alvo():
    num, cat = selecionar_features(PERFIL, alvo="quantidade")
    assert "cliente_id" not in num          # ID nao e feature
    assert "quantidade" not in num          # o alvo nao pode ser feature (leakage!)
    assert set(num) == {"preco", "avaliacao"}
    assert cat == ["categoria"]


def test_avaliar_predicoes_perfeitas():
    y = np.array([1.0, 2.0, 3.0])
    metricas = avaliar_predicoes(y, y)      # previsao identica ao real
    assert metricas["MAE"] == 0.0
    assert metricas["R2"] == 1.0


def test_treinar_e_comparar_retorna_tabela():
    rng = np.random.default_rng(0)
    n = 200
    df = pd.DataFrame(
        {
            "preco": rng.uniform(10, 1000, n),
            "avaliacao": rng.uniform(1, 5, n),
            "categoria": rng.choice(["A", "B"], n),
            "cliente_id": rng.integers(1, 999, n),
        }
    )
    # alvo com relacao clara -> um bom modelo tem que bater o baseline
    df["quantidade"] = 10 - 0.005 * df["preco"] + rng.normal(0, 0.5, n)

    tabela = treinar_e_comparar(df, PERFIL, alvo="quantidade")

    assert set(tabela.columns) == {"modelo", "MAE", "RMSE", "R2"}
    assert len(tabela) == 4                          # 4 modelos comparados
    # o melhor modelo (topo) precisa superar o baseline
    baseline_r2 = tabela.loc[tabela["modelo"].str.contains("Baseline"), "R2"].iloc[0]
    assert tabela.iloc[0]["R2"] > baseline_r2
