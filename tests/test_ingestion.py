"""Testes da camada de ingestao.

Usamos a fixture `tmp_path` do pytest: ela cria uma pasta temporaria isolada
para cada teste. Assim os testes sao AUTOCONTIDOS -- nao dependem de nenhum
arquivo externo e nao sujam o projeto.
"""
import pandas as pd
import pytest

from app.ingestion import ErroDeIngestao, carregar_csv

CSV_VALIDO = (
    "produto,preco,quantidade\n"
    "Notebook,3499.90,1\n"
    "Mouse,149.90,3\n"
)


def test_carrega_csv_valido(tmp_path):
    """Um CSV bem formado deve virar um DataFrame com as dimensoes certas."""
    arquivo = tmp_path / "vendas.csv"
    arquivo.write_text(CSV_VALIDO, encoding="utf-8")

    df = carregar_csv(arquivo)

    assert isinstance(df, pd.DataFrame)
    assert df.shape == (2, 3)
    assert list(df.columns) == ["produto", "preco", "quantidade"]


def test_arquivo_inexistente_gera_erro():
    """Caminho que nao existe deve levantar nossa excecao, nao a do pandas."""
    with pytest.raises(ErroDeIngestao, match="nao encontrado"):
        carregar_csv("caminho/que/nao/existe.csv")


def test_extensao_invalida_gera_erro(tmp_path):
    """Arquivo que nao e .csv deve ser barrado na porta."""
    arquivo = tmp_path / "dados.txt"
    arquivo.write_text("qualquer coisa", encoding="utf-8")

    with pytest.raises(ErroDeIngestao, match="Extensao invalida"):
        carregar_csv(arquivo)


def test_csv_so_com_cabecalho_gera_erro(tmp_path):
    """CSV com cabecalho mas sem linhas de dados e inutil -> erro."""
    arquivo = tmp_path / "vazio.csv"
    arquivo.write_text("produto,preco,quantidade\n", encoding="utf-8")

    with pytest.raises(ErroDeIngestao, match="sem linhas de dados"):
        carregar_csv(arquivo)


def test_fallback_de_encoding_latin1(tmp_path):
    """Arquivo em latin-1 (Excel BR) deve ser lido pelo fallback, sem crashar."""
    arquivo = tmp_path / "acentos.csv"
    conteudo = "produto,secao\nCadeira,Móveis\n"
    arquivo.write_bytes(conteudo.encode("latin-1"))

    df = carregar_csv(arquivo)  # encoding padrao utf-8 falha e cai p/ latin-1

    assert df.shape == (1, 2)
    assert df.loc[0, "secao"] == "Móveis"
