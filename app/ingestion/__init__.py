"""Camada de Ingestao: carregamento confiavel de arquivos de dados."""
from app.ingestion.loader import ErroDeIngestao, carregar_csv

__all__ = ["carregar_csv", "ErroDeIngestao"]
