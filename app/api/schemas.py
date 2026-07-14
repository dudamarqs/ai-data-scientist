"""Contratos de entrada/saida da API (Pydantic).

Pydantic valida os dados na porta de entrada: se o cliente mandar lixo,
a requisicao e rejeitada com 422 ANTES de tocar na nossa logica (fail-fast).
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DatasetCriado(BaseModel):
    dataset_id: str
    linhas: int
    colunas: int
    duplicatas_removidas: int
    perfil: dict[str, str] = Field(
        description="Tipo semantico detectado de cada coluna."
    )


class Pergunta(BaseModel):
    texto: str = Field(min_length=3, max_length=1000, examples=["Existe sazonalidade?"])


class ChamadaFerramenta(BaseModel):
    """Um passo dos bastidores: prova de que o numero veio do Python, nao do LLM."""

    ferramenta: str
    argumentos: dict[str, Any]
    resultado: str


class Resposta(BaseModel):
    pergunta: str
    resposta: str
    bastidores: list[ChamadaFerramenta] = Field(
        default_factory=list,
        description="Ferramentas que o LLM pediu e o que o nosso codigo calculou.",
    )


class Preview(BaseModel):
    colunas: list[str]
    linhas: list[dict[str, Any]]
    total_linhas: int


class Grafico(BaseModel):
    titulo: str
    figura: dict[str, Any] = Field(description="Figura do Plotly em JSON.")


class Graficos(BaseModel):
    graficos: list[Grafico]
