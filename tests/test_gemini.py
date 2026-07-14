"""Testes do adaptador Gemini (traducao entre os dois 'dialetos')."""
from types import SimpleNamespace

import pytest

from app.llm.gemini import BlocoFerramenta, BlocoTexto, ClienteGemini
from app.llm.tools import FERRAMENTAS


@pytest.fixture
def adaptador(monkeypatch):
    """Cria o adaptador sem tocar na API real do Google."""
    monkeypatch.setattr("app.llm.gemini.genai.Client", lambda api_key: object())
    return ClienteGemini(api_key="chave-falsa")


def _resposta_gemini(partes):
    """Imita o formato de resposta do Gemini: candidates[0].content.parts"""
    conteudo = SimpleNamespace(parts=partes)
    return SimpleNamespace(candidates=[SimpleNamespace(content=conteudo)])


def test_traduz_ferramentas_para_o_formato_do_gemini(adaptador):
    ferramenta = adaptador._traduzir_ferramentas(FERRAMENTAS)
    nomes = [f.name for f in ferramenta.function_declarations]

    assert "correlacao" in nomes
    assert "treinar_modelos" in nomes
    # o JSON Schema da nossa ferramenta passa direto, sem reescrever
    correlacao = next(f for f in ferramenta.function_declarations if f.name == "correlacao")
    assert "metodo" in correlacao.parameters_json_schema["properties"]


def test_resposta_com_texto_vira_bloco_de_texto(adaptador):
    parte = SimpleNamespace(function_call=None, text="O preco tipico e R$ 949,90.")

    resposta = adaptador._traduzir_resposta(_resposta_gemini([parte]))

    assert resposta.stop_reason == "end_turn"
    assert isinstance(resposta.content[0], BlocoTexto)
    assert resposta.content[0].text == "O preco tipico e R$ 949,90."


def test_pedido_de_funcao_vira_bloco_tool_use(adaptador):
    chamada = SimpleNamespace(name="correlacao", args={"metodo": "pearson"})
    parte = SimpleNamespace(function_call=chamada, text=None)

    resposta = adaptador._traduzir_resposta(_resposta_gemini([parte]))

    assert resposta.stop_reason == "tool_use"      # o orquestrador vai executar
    bloco = resposta.content[0]
    assert isinstance(bloco, BlocoFerramenta)
    assert bloco.name == "correlacao"
    assert bloco.input == {"metodo": "pearson"}
    # o adaptador precisa lembrar id -> nome (o Gemini exige o nome na volta)
    assert adaptador._nome_por_id[bloco.id] == "correlacao"


def test_traduz_historico_completo_ida_e_volta(adaptador):
    """O ciclo inteiro: pergunta -> pedido de ferramenta -> resultado."""
    adaptador._nome_por_id["call_1"] = "correlacao"
    mensagens = [
        {"role": "user", "content": "Preco e quantidade tem relacao?"},
        {
            "role": "assistant",
            "content": [BlocoFerramenta(id="call_1", name="correlacao", input={})],
        },
        {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": "call_1", "content": "r = -0.63"}
            ],
        },
    ]

    conteudos = adaptador._traduzir_mensagens(mensagens)

    assert [c.role for c in conteudos] == ["user", "model", "user"]
    # 'assistant' virou 'model' e o bloco tool_use virou function_call
    assert conteudos[1].parts[0].function_call.name == "correlacao"
    # o tool_result virou function_response, com o NOME recuperado pelo de-para
    resposta_funcao = conteudos[2].parts[0].function_response
    assert resposta_funcao.name == "correlacao"
    assert resposta_funcao.response == {"resultado": "r = -0.63"}
