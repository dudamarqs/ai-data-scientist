"""
Camada de API (FastAPI) - a porta de entrada do sistema.

Rotas:
  GET  /                               -> a interface web (frontend)
  POST /datasets                       -> envia um CSV, recebe um dataset_id
  GET  /datasets/{id}                  -> perfil semantico do dataset
  GET  /datasets/{id}/preview          -> primeiras linhas (tabela)
  GET  /datasets/{id}/graficos         -> figuras do Plotly (JSON)
  POST /datasets/{id}/perguntar        -> conversa com os dados (LLM)
"""
from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.analysis.charts import gerar_graficos, preview
from app.api.repository import RepositorioDeDatasets, repositorio
from app.api.schemas import (
    DatasetCriado,
    Graficos,
    Pergunta,
    Preview,
    Resposta,
)
from app.core import config
from app.core.pipeline import DatasetPreparado, preparar
from app.ingestion import ErroDeIngestao
from app.llm import CaixaDeFerramentas, OrquestradorLLM, descrever_dataset
from app.llm.factory import ProvedorNaoConfigurado, criar_cliente

DIRETORIO_WEB = Path(__file__).resolve().parent.parent / "web"

app = FastAPI(
    title="AI Data Scientist",
    description="Envie um CSV e converse com seus dados em linguagem natural.",
    version="1.0.0",
)

# Serve o CSS/JS. A pagina em si tem rota propria (abaixo) para nao competir
# com as rotas da API -- por isso montamos so /static, e nao a raiz.
app.mount("/static", StaticFiles(directory=DIRETORIO_WEB), name="static")


def obter_repositorio() -> RepositorioDeDatasets:
    """Dependency injection: em testes, sobrescrevemos por um repo limpo."""
    return repositorio


def _buscar_ou_404(repo: RepositorioDeDatasets, dataset_id: str) -> DatasetPreparado:
    dataset = repo.buscar(dataset_id)
    if dataset is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dataset nao encontrado.")
    return dataset


def _resumo(dataset_id: str, dataset: DatasetPreparado) -> DatasetCriado:
    return DatasetCriado(
        dataset_id=dataset_id,
        linhas=len(dataset.df),
        colunas=len(dataset.df.columns),
        duplicatas_removidas=dataset.duplicatas_removidas,
        perfil={c: t.value for c, t in dataset.perfil.items()},
    )


@app.get("/", include_in_schema=False)
def pagina_inicial() -> FileResponse:
    """A interface web."""
    return FileResponse(DIRETORIO_WEB / "index.html")


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

    return _resumo(repo.salvar(dataset), dataset)


@app.get("/datasets/{dataset_id}", response_model=DatasetCriado, tags=["dados"])
def ver_dataset(
    dataset_id: str,
    repo: RepositorioDeDatasets = Depends(obter_repositorio),
) -> DatasetCriado:
    return _resumo(dataset_id, _buscar_ou_404(repo, dataset_id))


@app.get("/datasets/{dataset_id}/preview", response_model=Preview, tags=["dados"])
def ver_preview(
    dataset_id: str,
    linhas: int = 10,
    repo: RepositorioDeDatasets = Depends(obter_repositorio),
) -> Preview:
    """Primeiras linhas, para a tabela do frontend."""
    dataset = _buscar_ou_404(repo, dataset_id)
    return Preview(**preview(dataset.df, linhas=min(linhas, 50)))


@app.get("/datasets/{dataset_id}/graficos", response_model=Graficos, tags=["dados"])
def ver_graficos(
    dataset_id: str,
    repo: RepositorioDeDatasets = Depends(obter_repositorio),
) -> Graficos:
    """Histogramas + mapa de correlacao, gerados no servidor (Plotly)."""
    dataset = _buscar_ou_404(repo, dataset_id)
    return Graficos(graficos=gerar_graficos(dataset.df, dataset.perfil))


@app.post("/datasets/{dataset_id}/perguntar", response_model=Resposta, tags=["llm"])
def perguntar(
    dataset_id: str,
    pergunta: Pergunta,
    repo: RepositorioDeDatasets = Depends(obter_repositorio),
) -> Resposta:
    """Conversa com os dados: o LLM orquestra, o nosso codigo calcula."""
    dataset = _buscar_ou_404(repo, dataset_id)

    try:
        cliente, modelo = criar_cliente()  # Gemini ou Claude, conforme o .env
    except ProvedorNaoConfigurado as erro:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(erro)) from erro

    orquestrador = OrquestradorLLM(
        ferramentas=CaixaDeFerramentas(dataset.df, dataset.perfil),
        contexto_dataset=descrever_dataset(dataset.df, dataset.perfil),
        cliente=cliente,
        modelo=modelo,
    )
    resultado = orquestrador.perguntar_com_bastidores(pergunta.texto)

    return Resposta(
        pergunta=pergunta.texto,
        resposta=resultado.resposta,
        bastidores=[
            {
                "ferramenta": c.ferramenta,
                "argumentos": c.argumentos,
                "resultado": c.resultado,
            }
            for c in resultado.bastidores
        ],
    )
