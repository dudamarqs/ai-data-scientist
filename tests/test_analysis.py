"""Testes da camada de analise (EDA)."""
import pandas as pd

from app.analysis import (
    colunas_por_tipo,
    estatisticas_descritivas,
    matriz_correlacao,
    resumo_categorico,
)
from app.profiling import TipoSemantico

PERFIL = {
    "preco": TipoSemantico.MOEDA,
    "quantidade": TipoSemantico.NUMERICO,
    "cliente_id": TipoSemantico.IDENTIFICADOR,
    "categoria": TipoSemantico.CATEGORIA,
}

DF = pd.DataFrame(
    {
        "preco": [10.0, 20.0, 30.0, 40.0],
        "quantidade": [1, 2, 3, 4],
        "cliente_id": [1001, 1002, 1003, 1004],
        "categoria": ["A", "B", "A", "A"],
    }
)


def test_colunas_por_tipo_ignora_identificador():
    cols = colunas_por_tipo(PERFIL, {TipoSemantico.MOEDA, TipoSemantico.NUMERICO})
    assert cols == ["preco", "quantidade"]      # cliente_id NAO entra


def test_estatisticas_nao_incluem_identificador():
    resumo = estatisticas_descritivas(DF, PERFIL)
    assert set(resumo.index) == {"preco", "quantidade"}   # sem cliente_id
    assert "mediana" in resumo.columns
    assert "assimetria" in resumo.columns
    assert resumo.loc["preco", "mediana"] == 25.0         # mediana de [10,20,30,40]


def test_correlacao_perfeita_positiva():
    # preco e quantidade sobem juntos linearmente -> r = 1.0
    corr = matriz_correlacao(DF, PERFIL)
    assert round(corr.loc["preco", "quantidade"], 5) == 1.0


def test_resumo_categorico_conta_valores():
    resumo = resumo_categorico(DF, PERFIL)
    assert "categoria" in resumo
    assert resumo["categoria"]["A"] == 3        # 'A' aparece 3 vezes
