"""
Fabrica de clientes LLM (Padrao FACTORY).

Um unico lugar decide QUAL provedor usar, lendo a configuracao. O resto do
sistema pede "me da um cliente" e nao precisa saber se e Gemini ou Claude.

Trocar de provedor = mudar uma variavel no .env. Nenhuma linha de codigo.
"""
from __future__ import annotations

from app.core import config


class ProvedorNaoConfigurado(Exception):
    """Falta a chave de API do provedor escolhido."""


def criar_cliente() -> tuple[object, str]:
    """Devolve (cliente, nome_do_modelo) conforme o .env.

    Raises:
        ProvedorNaoConfigurado: se a chave do provedor escolhido nao existir.
    """
    provedor = config.PROVEDOR_LLM

    if provedor == "gemini":
        if not config.GOOGLE_API_KEY:
            raise ProvedorNaoConfigurado(
                "GOOGLE_API_KEY nao configurada. Pegue a chave gratuita em "
                "https://aistudio.google.com/apikey e coloque no arquivo .env."
            )
        from app.llm.gemini import ClienteGemini

        return ClienteGemini(api_key=config.GOOGLE_API_KEY), config.MODELO_GEMINI

    if provedor == "claude":
        if not config.ANTHROPIC_API_KEY:
            raise ProvedorNaoConfigurado(
                "ANTHROPIC_API_KEY nao configurada. Pegue em "
                "https://console.anthropic.com e coloque no arquivo .env."
            )
        import anthropic

        return anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY), config.MODELO_CLAUDE

    raise ProvedorNaoConfigurado(
        f"PROVEDOR_LLM invalido: '{provedor}'. Use 'gemini' ou 'claude'."
    )
