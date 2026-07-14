"""
Camada de Orquestracao LLM - o MAESTRO.

Implementa o "loop agentico" (Tool Use):
  1. Manda a pergunta + a lista de ferramentas para o LLM.
  2. Se o LLM pedir uma ferramenta (stop_reason == 'tool_use'),
     NOSSO CODIGO executa e devolve o resultado.
  3. Repete ate o LLM ter tudo que precisa e responder em portugues.

O LLM decide O QUE fazer. Ele nunca calcula. Isso elimina alucinacao numerica.

IMPORTANTE: este arquivo NAO importa nenhum SDK de provedor. Ele depende apenas
do PROTOCOLO abaixo (uma "interface"). Quem entrega um cliente concreto e a
factory. Por isso trocar Claude <-> Gemini nao mexe em nada aqui.
"""
from __future__ import annotations

from typing import Any, Protocol

from app.llm.tools import FERRAMENTAS, CaixaDeFerramentas

MAX_ITERACOES = 8  # trava de seguranca: impede loop infinito de ferramentas

PROMPT_SISTEMA = """Voce e um cientista de dados senior conversando em portugues do Brasil.

REGRA ABSOLUTA: voce NUNCA calcula numeros de cabeca. Para qualquer estatistica,
correlacao, contagem, previsao ou importancia de variaveis, voce DEVE chamar a
ferramenta correspondente e usar o resultado retornado. Inventar numeros e
inaceitavel.

Ao responder:
- Explique em linguagem simples, como se fosse para alguem de negocios.
- Cite os numeros exatos que as ferramentas retornaram.
- Se citar uma correlacao, lembre o usuario de que correlacao nao prova causalidade.
- Se a amostra for pequena, avise que o resultado e pouco confiavel.

Dados disponiveis nesta sessao:
{contexto_dataset}
"""


class ClienteLLM(Protocol):
    """O CONTRATO que qualquer provedor precisa cumprir para servir de maestro.

    Tanto o SDK da Anthropic quanto o nosso ClienteGemini satisfazem isto.
    Programar contra a interface (e nao contra a implementacao) e o "D" do SOLID:
    Dependency Inversion.
    """

    messages: Any  # precisa expor .messages.create(...)


class OrquestradorLLM:
    """O maestro: traduz linguagem natural <-> ferramentas de dados."""

    def __init__(
        self,
        ferramentas: CaixaDeFerramentas,
        contexto_dataset: str,
        *,
        cliente: ClienteLLM,
        modelo: str,
    ) -> None:
        self._cliente = cliente
        self._ferramentas = ferramentas
        self._modelo = modelo
        self._sistema = PROMPT_SISTEMA.format(contexto_dataset=contexto_dataset)

    def perguntar(self, pergunta: str) -> str:
        """Responde uma pergunta em linguagem natural sobre os dados."""
        mensagens: list[dict] = [{"role": "user", "content": pergunta}]

        for _ in range(MAX_ITERACOES):
            resposta = self._cliente.messages.create(
                model=self._modelo,
                max_tokens=8000,
                system=self._sistema,
                tools=FERRAMENTAS,
                messages=mensagens,
            )

            if resposta.stop_reason != "tool_use":
                return self._extrair_texto(resposta)

            # O LLM pediu ferramentas: executamos TODAS e devolvemos juntas.
            mensagens.append({"role": "assistant", "content": resposta.content})
            resultados = [
                {
                    "type": "tool_result",
                    "tool_use_id": bloco.id,
                    "content": self._ferramentas.executar(bloco.name, bloco.input),
                }
                for bloco in resposta.content
                if bloco.type == "tool_use"
            ]
            mensagens.append({"role": "user", "content": resultados})

        return "Nao consegui concluir: limite de chamadas de ferramentas atingido."

    @staticmethod
    def _extrair_texto(resposta: Any) -> str:
        return "\n".join(
            bloco.text for bloco in resposta.content if bloco.type == "text"
        ).strip()
