"""Armazenamento dos datasets da sessao.

DIVIDA TECNICA CONSCIENTE: guardamos em memoria (dict). Isso significa que
reiniciar o servidor perde tudo, e nao funciona com varios processos/replicas.
Em producao isto vira Redis (cache) + PostgreSQL (metadados) + S3 (arquivos).
Isolamos atras desta classe justamente para poder trocar depois sem tocar na API.
"""
from __future__ import annotations

from uuid import uuid4

from app.core.pipeline import DatasetPreparado


class RepositorioDeDatasets:
    def __init__(self) -> None:
        self._itens: dict[str, DatasetPreparado] = {}

    def salvar(self, dataset: DatasetPreparado) -> str:
        dataset_id = uuid4().hex[:12]
        self._itens[dataset_id] = dataset
        return dataset_id

    def buscar(self, dataset_id: str) -> DatasetPreparado | None:
        return self._itens.get(dataset_id)


repositorio = RepositorioDeDatasets()
