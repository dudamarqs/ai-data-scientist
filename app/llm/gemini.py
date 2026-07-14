"""
Adaptador do Google Gemini (Padrao ADAPTER).

O problema: nosso OrquestradorLLM foi escrito falando o "dialeto Anthropic"
(client.messages.create(...) -> resposta com .content e .stop_reason).
O Gemini fala outro dialeto (client.models.generate_content(...) -> candidates).

A solucao: este arquivo e um TRADUTOR. Ele finge ser o cliente da Anthropic,
mas por baixo conversa com o Gemini. Resultado: o orquestrador, as ferramentas,
o pipeline e todas as 8 camadas de dados NAO MUDAM UMA LINHA.

Isso e o Padrao Adapter -- o mesmo motivo de termos criado ErroDeIngestao
encapsulando o pandas: proteger o sistema de detalhes de bibliotecas externas.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from google import genai
from google.genai import types


# --- Blocos no formato que o orquestrador ja entende (dialeto Anthropic) ---
@dataclass
class BlocoTexto:
    text: str
    type: str = "text"


@dataclass
class BlocoFerramenta:
    id: str
    name: str
    input: dict[str, Any]
    type: str = "tool_use"
    # PECULIARIDADE DO GEMINI: ele devolve uma "assinatura do pensamento" junto
    # com o pedido de funcao, e EXIGE que ela volte no historico. Sem isso, a
    # segunda chamada falha com 400. Guardamos aqui para reenviar depois.
    # Este detalhe fica PRESO no adaptador -- o resto do sistema nem sabe que existe.
    assinatura: bytes | None = None


@dataclass
class RespostaAdaptada:
    content: list[BlocoTexto | BlocoFerramenta]
    stop_reason: str


class ClienteGemini:
    """Imita a interface `cliente.messages.create(...)` do SDK da Anthropic."""

    def __init__(self, api_key: str) -> None:
        self._gemini = genai.Client(api_key=api_key)
        # O Gemini exige o NOME da funcao ao devolver o resultado, mas o dialeto
        # Anthropic so carrega o tool_use_id. Guardamos o de-para aqui.
        self._nome_por_id: dict[str, str] = {}
        self._contador = 0
        self.messages = self  # permite escrever cliente.messages.create(...)

    def create(
        self,
        *,
        model: str,
        max_tokens: int,
        system: str,
        tools: list[dict[str, Any]],
        messages: list[dict[str, Any]],
        **_ignorados: Any,
    ) -> RespostaAdaptada:
        resposta = self._gemini.models.generate_content(
            model=model,
            contents=self._traduzir_mensagens(messages),
            config=types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=max_tokens,
                tools=[self._traduzir_ferramentas(tools)],
            ),
        )
        return self._traduzir_resposta(resposta)

    # --- Tradução: NOSSO formato -> formato do Gemini ---

    @staticmethod
    def _traduzir_ferramentas(ferramentas: list[dict[str, Any]]) -> types.Tool:
        """Schemas JSON das nossas ferramentas -> FunctionDeclaration do Gemini."""
        return types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name=f["name"],
                    description=f["description"],
                    parameters_json_schema=f["input_schema"],
                )
                for f in ferramentas
            ]
        )

    def _traduzir_mensagens(self, mensagens: list[dict[str, Any]]) -> list[types.Content]:
        """Converte o histórico do dialeto Anthropic para o do Gemini.

        Anthropic: role 'assistant' | Gemini: role 'model'
        Anthropic: bloco tool_use   | Gemini: part function_call
        Anthropic: bloco tool_result| Gemini: part function_response
        """
        conteudos: list[types.Content] = []

        for mensagem in mensagens:
            papel = mensagem["role"]
            corpo = mensagem["content"]

            # Pergunta simples do usuario (texto puro)
            if isinstance(corpo, str):
                conteudos.append(
                    types.Content(role="user", parts=[types.Part.from_text(text=corpo)])
                )
                continue

            # Turno do modelo: texto e/ou pedidos de ferramenta
            if papel == "assistant":
                partes = []
                for bloco in corpo:
                    if bloco.type == "text":
                        partes.append(types.Part.from_text(text=bloco.text))
                    elif bloco.type == "tool_use":
                        # Reenviamos a assinatura do pensamento (exigencia do Gemini).
                        partes.append(
                            types.Part(
                                function_call=types.FunctionCall(
                                    name=bloco.name, args=bloco.input
                                ),
                                thought_signature=bloco.assinatura,
                            )
                        )
                conteudos.append(types.Content(role="model", parts=partes))
                continue

            # Resultados das ferramentas que NOS executamos
            partes = [
                types.Part.from_function_response(
                    name=self._nome_por_id.get(item["tool_use_id"], "desconhecida"),
                    response={"resultado": item["content"]},
                )
                for item in corpo
                if item.get("type") == "tool_result"
            ]
            conteudos.append(types.Content(role="user", parts=partes))

        return conteudos

    # --- Tradução: formato do Gemini -> NOSSO formato ---

    def _traduzir_resposta(self, resposta: Any) -> RespostaAdaptada:
        blocos: list[BlocoTexto | BlocoFerramenta] = []
        pediu_ferramenta = False

        candidatos = getattr(resposta, "candidates", None) or []
        partes = []
        if candidatos and candidatos[0].content:
            partes = candidatos[0].content.parts or []

        for parte in partes:
            chamada = getattr(parte, "function_call", None)
            if chamada is not None:
                pediu_ferramenta = True
                self._contador += 1
                identificador = f"call_{self._contador}"
                self._nome_por_id[identificador] = chamada.name
                blocos.append(
                    BlocoFerramenta(
                        id=identificador,
                        name=chamada.name,
                        input=dict(chamada.args or {}),
                        assinatura=getattr(parte, "thought_signature", None),
                    )
                )
            elif getattr(parte, "text", None):
                blocos.append(BlocoTexto(text=parte.text))

        return RespostaAdaptada(
            content=blocos,
            stop_reason="tool_use" if pediu_ferramenta else "end_turn",
        )
