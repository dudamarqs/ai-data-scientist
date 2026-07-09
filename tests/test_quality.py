"""Testes da camada de qualidade de dados."""
import numpy as np
import pandas as pd
import pytest

from app.quality import converter_moeda_brl, preencher_faltantes, remover_duplicatas


def test_remover_duplicatas():
    df = pd.DataFrame({"produto": ["A", "B", "A"], "preco": [10, 20, 10]})
    limpo = remover_duplicatas(df)
    assert limpo.shape == (2, 2)          # a 3a linha (A,10) era duplicata
    assert list(limpo.index) == [0, 1]    # indice foi reiniciado


def test_converter_moeda_brl_valores_validos():
    serie = pd.Series(["R$ 3.499,90", "R$ 149,90", "R$ 1.299,90"])
    resultado = converter_moeda_brl(serie)
    assert resultado.tolist() == [3499.90, 149.90, 1299.90]


def test_converter_moeda_brl_valor_invalido_vira_nan():
    serie = pd.Series(["R$ 99,90", "indisponivel"])
    resultado = converter_moeda_brl(serie)
    assert resultado.iloc[0] == 99.90
    assert np.isnan(resultado.iloc[1])    # 'indisponivel' -> NaN


def test_preencher_faltantes_mediana_e_robusta_a_outlier():
    # 9 valores em ~3 e um outlier gigante; a mediana ignora o outlier.
    serie = pd.Series([3, 3, 3, 3, np.nan, 3, 3, 3, 3, 1000])
    resultado = preencher_faltantes(serie, estrategia="mediana")
    assert resultado.isna().sum() == 0    # nao sobrou NaN
    assert resultado.iloc[4] == 3.0       # preencheu com a mediana (3), nao a media


def test_preencher_faltantes_estrategia_invalida():
    serie = pd.Series([1.0, np.nan, 3.0])
    with pytest.raises(ValueError, match="Estrategia invalida"):
        preencher_faltantes(serie, estrategia="modinha")


def test_funcoes_nao_alteram_o_original():
    """Imutabilidade: limpar nao pode mexer no DataFrame de entrada."""
    df = pd.DataFrame({"produto": ["A", "A"], "preco": [10, 10]})
    _ = remover_duplicatas(df)
    assert df.shape == (2, 2)             # original intacto
