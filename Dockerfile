# === Estagio 1: BUILD (instala dependencias) ===
# Multi-stage build: as ferramentas de compilacao ficam neste estagio e NAO
# vao para a imagem final -> imagem menor e com menos superficie de ataque.
FROM python:3.12-slim AS builder

WORKDIR /build

# Copiamos SO o requirements primeiro. Assim, se o codigo mudar mas as
# dependencias nao, o Docker reaproveita o cache desta camada (build rapido).
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/instalado -r requirements.txt


# === Estagio 2: RUNTIME (a imagem que vai para producao) ===
FROM python:3.12-slim

# Nunca rode como root: se a aplicacao for invadida, o atacante fica preso
# num usuario sem privilegios.
RUN useradd --create-home --uid 1000 appuser

WORKDIR /app

# Traz apenas as bibliotecas ja instaladas, sem o lixo do build.
COPY --from=builder /instalado /usr/local
COPY --chown=appuser:appuser app/ ./app/

USER appuser

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

# Health check: o Docker/Kubernetes pergunta "voce esta vivo?" periodicamente.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/saude')"

CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
