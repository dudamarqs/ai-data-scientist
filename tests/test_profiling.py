"""Testes da camada de profiling (deteccao de tipos semanticos)."""
import pandas as pd

from app.profiling import TipoSemantico, detectar_tipo_semantico, perfilar


def test_detecta_identificador_pelo_nome():
    serie = pd.Series(["01310", "04567", "20040"])
    # mesmo parecendo numero, o NOME 'cep_loja' denuncia um identificador
    assert detectar_tipo_semantico(serie, "cep_loja") == TipoSemantico.IDENTIFICADOR


def test_detecta_moeda():
    serie = pd.Series(["R$ 3.499,90", "R$ 149,90", "R$ 1.299,90"])
    assert detectar_tipo_semantico(serie, "preco") == TipoSemantico.MOEDA


def test_detecta_data():
    serie = pd.Series(["05/01/2024", "06/01/2024", "07/02/2024"])
    assert detectar_tipo_semantico(serie, "data_venda") == TipoSemantico.DATA


def test_detecta_numerico():
    serie = pd.Series(["1", "3", "2", "4"])
    assert detectar_tipo_semantico(serie, "quantidade") == TipoSemantico.NUMERICO


def test_detecta_categoria_poucos_distintos():
    serie = pd.Series(["A", "B", "A", "B", "A", "C"])  # 3 distintos em 6 -> categoria
    assert detectar_tipo_semantico(serie, "categoria") == TipoSemantico.CATEGORIA


def test_detecta_texto_muitos_distintos():
    serie = pd.Series(["Notebook Dell", "Mouse Logitech", "Teclado", "Webcam Pro"])
    assert detectar_tipo_semantico(serie, "descricao") == TipoSemantico.TEXTO


def test_perfilar_retorna_schema_completo():
    df = pd.DataFrame(
        {
            "data_venda": ["05/01/2024", "06/01/2024"],
            "preco": ["R$ 10,00", "R$ 20,00"],
            "cliente_id": ["1001", "1002"],
            "quantidade": ["1", "3"],
        }
    )
    perfil = perfilar(df)
    assert perfil == {
        "data_venda": TipoSemantico.DATA,
        "preco": TipoSemantico.MOEDA,
        "cliente_id": TipoSemantico.IDENTIFICADOR,
        "quantidade": TipoSemantico.NUMERICO,
    }
