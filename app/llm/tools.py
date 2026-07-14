"""
Ferramentas que o LLM pode chamar (Tool Use).

Este e o CONTRATO entre o maestro (LLM) e a orquestra (nosso codigo):
- FERRAMENTAS: os schemas JSON que descrevem cada ferramenta ao LLM.
- CaixaDeFerramentas: quem EXECUTA de verdade, com pandas/sklearn.

O LLM NUNCA calcula. Ele so escolhe qual ferramenta chamar e com quais
argumentos. Toda matematica acontece aqui, de forma deterministica.
"""
from __future__ import annotations

import json
from typing import Any

import pandas as pd

from app.analysis import (
    estatisticas_descritivas,
    matriz_correlacao,
    resumo_categorico,
)
from app.analysis.modeling import treinar_e_comparar
from app.interpret import calcular_shap, importancia_global, treinar_para_explicar
from app.profiling import TipoSemantico

# Schemas em JSON Schema: e assim que o LLM "enxerga" nossas capacidades.
# A DESCRICAO e critica: e ela que ensina o LLM QUANDO usar cada ferramenta.
FERRAMENTAS: list[dict[str, Any]] = [
    {
        "name": "estatisticas_descritivas",
        "description": (
            "Retorna estatisticas descritivas (media, mediana, desvio-padrao, "
            "minimo, maximo, quartis, assimetria) das colunas numericas. "
            "Use quando o usuario perguntar sobre valores tipicos, medias, "
            "distribuicao ou resumo dos dados."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "correlacao",
        "description": (
            "Calcula a matriz de correlacao entre as colunas numericas. "
            "Use quando o usuario perguntar se duas variaveis tem relacao, "
            "quais variaveis andam juntas, ou pedir correlacoes."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "metodo": {
                    "type": "string",
                    "enum": ["pearson", "spearman"],
                    "description": "pearson (linear) ou spearman (monotonica).",
                }
            },
            "required": [],
        },
    },
    {
        "name": "contagem_por_categoria",
        "description": (
            "Conta quantas vezes cada valor aparece numa coluna categorica. "
            "Use para perguntas do tipo 'qual categoria mais vende' ou "
            "'quantos registros por tipo'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "coluna": {
                    "type": "string",
                    "description": "Nome da coluna categorica a contar.",
                }
            },
            "required": ["coluna"],
        },
    },
    {
        "name": "treinar_modelos",
        "description": (
            "Treina e compara varios modelos de Machine Learning para prever "
            "uma coluna-alvo, devolvendo as metricas (MAE, RMSE, R2) de cada um. "
            "Use quando o usuario pedir previsao, modelo preditivo ou quiser "
            "saber se e possivel prever algo."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "alvo": {
                    "type": "string",
                    "description": "Nome da coluna numerica que se quer prever.",
                }
            },
            "required": ["alvo"],
        },
    },
    {
        "name": "importancia_variaveis",
        "description": (
            "Calcula a importancia de cada variavel (SHAP) para prever a coluna-alvo. "
            "Use quando o usuario perguntar QUAIS fatores mais influenciam algo, "
            "o que explica um resultado, ou pedir a explicacao do modelo."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "alvo": {
                    "type": "string",
                    "description": "Nome da coluna numerica que se quer explicar.",
                }
            },
            "required": ["alvo"],
        },
    },
]


class CaixaDeFerramentas:
    """Executa as ferramentas de verdade sobre um DataFrame ja limpo e tipado."""

    def __init__(self, df: pd.DataFrame, perfil: dict[str, TipoSemantico]) -> None:
        self._df = df
        self._perfil = perfil

    def executar(self, nome: str, argumentos: dict[str, Any]) -> str:
        """Despacha a chamada do LLM para a funcao Python correspondente.

        Devolve SEMPRE texto (o LLM le texto). Erros viram mensagem de erro
        legivel, para o LLM poder se corrigir e tentar outra ferramenta.
        """
        try:
            despachante = {
                "estatisticas_descritivas": self._estatisticas,
                "correlacao": self._correlacao,
                "contagem_por_categoria": self._contagem,
                "treinar_modelos": self._treinar,
                "importancia_variaveis": self._importancia,
            }[nome]
        except KeyError:
            return f"Erro: ferramenta desconhecida '{nome}'."

        try:
            return despachante(**argumentos)
        except Exception as erro:  # devolvemos o erro ao LLM em vez de quebrar
            return f"Erro ao executar '{nome}': {type(erro).__name__}: {erro}"

    # --- implementacoes (o "trabalho pesado", deterministico) ---

    def _estatisticas(self) -> str:
        return estatisticas_descritivas(self._df, self._perfil).round(3).to_string()

    def _correlacao(self, metodo: str = "pearson") -> str:
        matriz = matriz_correlacao(self._df, self._perfil, metodo=metodo)
        aviso = ""
        if len(self._df) < 30:
            aviso = "\nATENCAO: amostra pequena (n<30) - correlacao pouco confiavel."
        return matriz.round(3).to_string() + aviso

    def _contagem(self, coluna: str) -> str:
        resumo = resumo_categorico(self._df, self._perfil)
        if coluna not in resumo:
            disponiveis = list(resumo) or "nenhuma"
            return f"Erro: '{coluna}' nao e categorica. Disponiveis: {disponiveis}."
        return resumo[coluna].to_string()

    def _treinar(self, alvo: str) -> str:
        tabela = treinar_e_comparar(self._df, self._perfil, alvo=alvo)
        return tabela.round(3).to_string(index=False)

    def _importancia(self, alvo: str) -> str:
        pipeline, X_teste = treinar_para_explicar(self._df, self._perfil, alvo=alvo)
        valores, nomes = calcular_shap(pipeline, X_teste.head(100))
        return importancia_global(valores, nomes).round(3).to_string()


def descrever_dataset(df: pd.DataFrame, perfil: dict[str, TipoSemantico]) -> str:
    """Contexto do dataset injetado no system prompt (o LLM precisa saber o que existe)."""
    colunas = {coluna: tipo.value for coluna, tipo in perfil.items()}
    return json.dumps(
        {"linhas": len(df), "colunas": colunas}, ensure_ascii=False, indent=2
    )
