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

# Servicos de hospedagem (Render, Cloud Run, HF Spaces) injetam a porta na
# variavel PORT. Caimos para 8000 quando rodando localmente.
ENV PORT=8000
EXPOSE 8000

# Health check: o Docker/Kubernetes pergunta "voce esta vivo?" periodicamente.
HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://localhost:%s/saude' % os.environ.get('PORT','8000'))"

# Forma "shell" para que ${PORT} seja expandido em tempo de execucao.
CMD ["sh", "-c", "uvicorn app.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
