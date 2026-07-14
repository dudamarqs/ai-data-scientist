"""
Camada de API (FastAPI) - a porta de entrada do sistema.

Rotas:
  POST /datasets                       -> envia um CSV, recebe um dataset_id
  GET  /datasets/{id}                  -> perfil semantico do dataset
  POST /datasets/{id}/perguntar        -> conversa com os dados (LLM)
"""
from __future__ import annotations

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status

from app.api.repository import RepositorioDeDatasets, repositorio
from app.api.schemas import DatasetCriado, Pergunta, Resposta
from app.core import config
from app.core.pipeline import DatasetPreparado, preparar
from app.ingestion import ErroDeIngestao
from app.llm import CaixaDeFerramentas, OrquestradorLLM, descrever_dataset

app = FastAPI(
    title="AI Data Scientist",
    description="Envie um CSV e converse com seus dados em linguagem natural.",
    version="0.1.0",
)


def obter_repositorio() -> RepositorioDeDatasets:
    """Dependency injection: em testes, sobrescrevemos por um repo limpo."""
    return repositorio


def _buscar_ou_404(repo: RepositorioDeDatasets, dataset_id: str) -> DatasetPreparado:
    dataset = repo.buscar(dataset_id)
    if dataset is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dataset nao encontrado.")
    return dataset


@app.get("/saude", tags=["infra"])
def saude() -> dict[str, str]:
    """Health check - usado por Docker/Kubernetes para saber se estamos vivos."""
    return {"status": "ok"}


@app.post("/datasets", response_model=DatasetCriado, tags=["dados"])
async def enviar_csv(
    arquivo: UploadFile = File(...),
    repo: RepositorioDeDatasets = Depends(obter_repositorio),
) -> DatasetCriado:
    """Recebe um CSV, roda o pipeline (ingestao -> profiling -> limpeza)."""
    conteudo = await arquivo.read()

    # Guarda de memoria: sem isto, um arquivo gigante derruba o servidor.
    if len(conteudo) > config.TAMANHO_MAXIMO_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"Arquivo maior que {config.TAMANHO_MAXIMO_MB} MB.",
        )

    config.DIRETORIO_UPLOADS.mkdir(parents=True, exist_ok=True)
    destino = config.DIRETORIO_UPLOADS / (arquivo.filename or "upload.csv")
    destino.write_bytes(conteudo)

    try:
        dataset = preparar(destino)
    except ErroDeIngestao as erro:
        # Traduzimos o erro da NOSSA camada para o protocolo HTTP.
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(erro)) from erro

    dataset_id = repo.salvar(dataset)
    return DatasetCriado(
        dataset_id=dataset_id,
        linhas=len(dataset.df),
        colunas=len(dataset.df.columns),
        duplicatas_removidas=dataset.duplicatas_removidas,
        perfil={c: t.value for c, t in dataset.perfil.items()},
    )


@app.get("/datasets/{dataset_id}", response_model=DatasetCriado, tags=["dados"])
def ver_dataset(
    dataset_id: str,
    repo: RepositorioDeDatasets = Depends(obter_repositorio),
) -> DatasetCriado:
    dataset = _buscar_ou_404(repo, dataset_id)
    return DatasetCriado(
        dataset_id=dataset_id,
        linhas=len(dataset.df),
        colunas=len(dataset.df.columns),
        duplicatas_removidas=dataset.duplicatas_removidas,
        perfil={c: t.value for c, t in dataset.perfil.items()},
    )


@app.post("/datasets/{dataset_id}/perguntar", response_model=Resposta, tags=["llm"])
def perguntar(
    dataset_id: str,
    pergunta: Pergunta,
    repo: RepositorioDeDatasets = Depends(obter_repositorio),
) -> Resposta:
    """Conversa com os dados: o LLM orquestra, o nosso codigo calcula."""
    dataset = _buscar_ou_404(repo, dataset_id)

    if not config.ANTHROPIC_API_KEY:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "ANTHROPIC_API_KEY nao configurada. Crie um arquivo .env com a chave.",
        )

    orquestrador = OrquestradorLLM(
        ferramentas=CaixaDeFerramentas(dataset.df, dataset.perfil),
        contexto_dataset=descrever_dataset(dataset.df, dataset.perfil),
    )
    return Resposta(pergunta=pergunta.texto, resposta=orquestrador.perguntar(pergunta.texto))
