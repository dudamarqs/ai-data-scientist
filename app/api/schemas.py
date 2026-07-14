"""Contratos de entrada/saida da API (Pydantic).

Pydantic valida os dados na porta de entrada: se o cliente mandar lixo,
a requisicao e rejeitada com 422 ANTES de tocar na nossa logica (fail-fast).
"""
from __future__ import annotations

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


class Resposta(BaseModel):
    pergunta: str
    resposta: str
