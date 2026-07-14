"""Camada de Interpretabilidade: explicacao de modelos com SHAP."""
from app.interpret.explainer import (
    calcular_shap,
    explicar_previsao,
    importancia_global,
    treinar_para_explicar,
)

__all__ = [
    "treinar_para_explicar",
    "calcular_shap",
    "importancia_global",
    "explicar_previsao",
]
