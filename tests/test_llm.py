"""Testes da camada LLM.

Nao chamamos a API de verdade (custa dinheiro e exige chave). Usamos um
CLIENTE FALSO (mock) que simula as respostas do Claude -- assim testamos o
LOOP e a EXECUCAO das ferramentas, que e o que realmente escrevemos.
"""
from dataclasses import dataclass, field

import pandas as pd
import pytest

from app.llm import CaixaDeFerramentas, OrquestradorLLM, descrever_dataset
from app.profiling import TipoSemantico

PERFIL = {
    "preco": TipoSemantico.MOEDA,
    "quantidade": TipoSemantico.NUMERICO,
    "categoria": TipoSemantico.CATEGORIA,
    "cliente_id": TipoSemantico.IDENTIFICADOR,
}
DF = pd.DataFrame(
    {
        "preco": [10.0, 20.0, 30.0, 40.0],
        "quantidade": [4, 3, 2, 1],
        "categoria": ["A", "B", "A", "A"],
        "cliente_id": [1, 2, 3, 4],
    }
)


# --- dublês que imitam os objetos do SDK da Anthropic ---
@dataclass
class BlocoTexto:
    text: str
    type: str = "text"


@dataclass
class BlocoFerramenta:
    id: str
    name: str
    input: dict
    type: str = "tool_use"


@dataclass
class RespostaFalsa:
    content: list
    stop_reason: str


class ClienteFalso:
    """Devolve respostas pre-programadas, em ordem, e grava o que recebeu."""

    def __init__(self, respostas: list[RespostaFalsa]) -> None:
        self._respostas = list(respostas)
        self.chamadas: list[dict] = []
        self.messages = self  # imita client.messages.create(...)

    def create(self, **kwargs):
        self.chamadas.append(kwargs)
        return self._respostas.pop(0)


@pytest.fixture
def caixa():
    return CaixaDeFerramentas(DF, PERFIL)


def test_ferramenta_correlacao_executa_de_verdade(caixa):
    saida = caixa.executar("correlacao", {})
    assert "preco" in saida and "quantidade" in saida
    assert "-1.0" in saida          # preco e quantidade sao perfeitamente inversos
    assert "cliente_id" not in saida  # identificador fica de fora
    assert "amostra pequena" in saida  # n=4 -> aviso automatico


def test_ferramenta_desconhecida_devolve_erro_em_vez_de_quebrar(caixa):
    assert "desconhecida" in caixa.executar("ferramenta_inventada", {})


def test_ranking_top_n_por_coluna(caixa):
    # DF do teste: preco [10,20,30,40], quantidade [4,3,2,1]
    saida = caixa.executar("ranking", {"coluna": "preco", "ordem": "maior", "n": 2})
    linhas = saida.strip().splitlines()
    assert len(linhas) == 3               # cabecalho + 2 linhas
    assert "40" in linhas[1]              # o maior preco vem primeiro


def test_ranking_ordem_menor(caixa):
    saida = caixa.executar("ranking", {"coluna": "preco", "ordem": "menor", "n": 1})
    assert "10" in saida                  # o menor preco


def test_ranking_coluna_inexistente_avisa(caixa):
    assert "nao existe" in caixa.executar("ranking", {"coluna": "inventada"})


def test_erro_na_execucao_vira_mensagem_para_o_llm(caixa):
    # coluna que nao e categorica -> erro tratado, nao excecao
    saida = caixa.executar("contagem_por_categoria", {"coluna": "preco"})
    assert "Erro" in saida


def test_loop_agentico_executa_ferramenta_e_devolve_resposta(caixa):
    """O coracao do modulo: LLM pede ferramenta -> nos executamos -> LLM responde."""
    cliente = ClienteFalso(
        [
            # 1a volta: o "LLM" pede a ferramenta de correlacao
            RespostaFalsa(
                content=[BlocoFerramenta(id="t1", name="correlacao", input={})],
                stop_reason="tool_use",
            ),
            # 2a volta: com o resultado em maos, responde em portugues
            RespostaFalsa(
                content=[BlocoTexto("Preco e quantidade tem correlacao -1.0.")],
                stop_reason="end_turn",
            ),
        ]
    )
    orquestrador = OrquestradorLLM(caixa, "ctx", cliente=cliente, modelo="modelo-falso")

    resposta = orquestrador.perguntar("Preco e quantidade tem relacao?")

    assert resposta == "Preco e quantidade tem correlacao -1.0."
    assert len(cliente.chamadas) == 2                     # duas voltas no loop
    # a 2a chamada precisa conter o tool_result que NOS calculamos
    ultimas_msgs = cliente.chamadas[1]["messages"]
    tool_result = ultimas_msgs[-1]["content"][0]
    assert tool_result["type"] == "tool_result"
    assert tool_result["tool_use_id"] == "t1"
    assert "-1.0" in tool_result["content"]              # o numero veio do pandas!


def test_bastidores_registram_a_ferramenta_e_o_resultado(caixa):
    """Os bastidores sao a AUDITORIA: provam que o numero veio do Python."""
    cliente = ClienteFalso(
        [
            RespostaFalsa(
                content=[BlocoFerramenta(id="t1", name="correlacao", input={})],
                stop_reason="tool_use",
            ),
            RespostaFalsa(
                content=[BlocoTexto("Correlacao perfeita negativa.")],
                stop_reason="end_turn",
            ),
        ]
    )
    orquestrador = OrquestradorLLM(caixa, "ctx", cliente=cliente, modelo="modelo-falso")

    resultado = orquestrador.perguntar_com_bastidores("Tem relacao?")

    assert resultado.resposta == "Correlacao perfeita negativa."
    assert len(resultado.bastidores) == 1
    passo = resultado.bastidores[0]
    assert passo.ferramenta == "correlacao"
    assert "-1.0" in passo.resultado      # o numero real, calculado pelo pandas


def test_loop_tem_trava_contra_loop_infinito(caixa):
    """Se o LLM pedir ferramenta pra sempre, o loop precisa parar."""
    pedido_infinito = RespostaFalsa(
        content=[BlocoFerramenta(id="t", name="correlacao", input={})],
        stop_reason="tool_use",
    )
    cliente = ClienteFalso([pedido_infinito] * 50)
    orquestrador = OrquestradorLLM(caixa, "ctx", cliente=cliente, modelo="modelo-falso")

    resposta = orquestrador.perguntar("loop!")

    assert "limite de chamadas" in resposta
    assert len(cliente.chamadas) == 8                    # MAX_ITERACOES


def test_descrever_dataset_lista_colunas_e_tipos():
    contexto = descrever_dataset(DF, PERFIL)
    assert '"linhas": 4' in contexto
    assert "identificador" in contexto
