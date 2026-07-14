"""Testes da API (FastAPI TestClient - nao sobe servidor de verdade)."""
import pytest
from fastapi.testclient import TestClient

from app.api.main import app, obter_repositorio
from app.api.repository import RepositorioDeDatasets

CSV = (
    "data_venda,produto,categoria,preco,cliente_id\n"
    '05/01/2024,Notebook,Eletronicos,"R$ 3.499,90",01310\n'
    '06/01/2024,Mouse,Acessorios,"R$ 149,90",01310\n'
    '07/02/2024,Mouse,Acessorios,"R$ 149,90",04567\n'
    '05/01/2024,Notebook,Eletronicos,"R$ 3.499,90",01310\n'  # duplicata proposital
)


@pytest.fixture
def cliente():
    """Cada teste recebe um repositorio limpo (isolamento)."""
    repo = RepositorioDeDatasets()
    app.dependency_overrides[obter_repositorio] = lambda: repo
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_health_check(cliente):
    assert cliente.get("/saude").json() == {"status": "ok"}


def test_upload_roda_o_pipeline_completo(cliente, tmp_path):
    resposta = cliente.post("/datasets", files={"arquivo": ("v.csv", CSV, "text/csv")})

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["linhas"] == 3                     # 4 linhas - 1 duplicata
    assert corpo["duplicatas_removidas"] == 1
    assert corpo["perfil"]["preco"] == "moeda"      # profiling funcionou
    assert corpo["perfil"]["cliente_id"] == "identificador"
    assert corpo["perfil"]["data_venda"] == "data"
    assert corpo["dataset_id"]


def test_arquivo_nao_csv_e_rejeitado(cliente):
    resposta = cliente.post(
        "/datasets", files={"arquivo": ("foto.png", b"binario", "image/png")}
    )
    assert resposta.status_code == 400


def test_dataset_inexistente_da_404(cliente):
    assert cliente.get("/datasets/naoexiste").status_code == 404


@pytest.mark.parametrize(
    ("provedor", "chave_esperada"),
    [("gemini", "GOOGLE_API_KEY"), ("claude", "ANTHROPIC_API_KEY")],
)
def test_pergunta_sem_chave_de_api_da_503(cliente, monkeypatch, provedor, chave_esperada):
    """Sem chave, a API avisa educadamente (503) -- para qualquer provedor."""
    from app.core import config

    monkeypatch.setattr(config, "PROVEDOR_LLM", provedor)
    monkeypatch.setattr(config, "GOOGLE_API_KEY", None)
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", None)

    dataset_id = cliente.post(
        "/datasets", files={"arquivo": ("v.csv", CSV, "text/csv")}
    ).json()["dataset_id"]

    resposta = cliente.post(
        f"/datasets/{dataset_id}/perguntar", json={"texto": "Qual o preco medio?"}
    )
    assert resposta.status_code == 503
    assert chave_esperada in resposta.json()["detail"]


def test_pergunta_curta_demais_e_rejeitada_pelo_pydantic(cliente):
    dataset_id = cliente.post(
        "/datasets", files={"arquivo": ("v.csv", CSV, "text/csv")}
    ).json()["dataset_id"]

    resposta = cliente.post(f"/datasets/{dataset_id}/perguntar", json={"texto": "oi"})
    assert resposta.status_code == 422      # validacao automatica do Pydantic
