"""Configuracao central (lida do ambiente / arquivo .env).

NUNCA colocamos segredos no codigo. O .env fica fora do Git (.gitignore).
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Qual LLM usar: "gemini" (free tier do Google) ou "claude" (pago).
PROVEDOR_LLM: str = os.getenv("PROVEDOR_LLM", "gemini").lower()

# Chaves. Ausente -> a rota /perguntar responde 503 (em vez de crashar).
GOOGLE_API_KEY: str | None = os.getenv("GOOGLE_API_KEY")
ANTHROPIC_API_KEY: str | None = os.getenv("ANTHROPIC_API_KEY")

MODELO_GEMINI: str = os.getenv("MODELO_GEMINI", "gemini-2.5-flash")
MODELO_CLAUDE: str = os.getenv("MODELO_CLAUDE", "claude-opus-4-8")

# Limite de upload: protege a RAM do servidor (um CSV de 5 GB derrubaria tudo).
TAMANHO_MAXIMO_MB: int = int(os.getenv("TAMANHO_MAXIMO_MB", "50"))
TAMANHO_MAXIMO_BYTES: int = TAMANHO_MAXIMO_MB * 1024 * 1024

DIRETORIO_UPLOADS = Path(os.getenv("DIRETORIO_UPLOADS", "data/uploads"))
