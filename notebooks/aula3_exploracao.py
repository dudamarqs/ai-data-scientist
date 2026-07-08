"""
Aula 3 - Primeira leitura de dados na mao.
Objetivo: LER e INVESTIGAR, sem limpar nada ainda.
Rode com o Python do venv:
    .venv\\Scripts\\python.exe notebooks/aula3_exploracao.py
"""
import pandas as pd

CAMINHO = "data/vendas_exemplo.csv"

# 1) Leitura crua: deixamos o pandas "chutar" tudo sozinho.
df = pd.read_csv(CAMINHO)

print("=" * 60)
print("1) .head() -> as primeiras linhas (visao rapida dos dados)")
print("=" * 60)
print(df.head())

print("\n" + "=" * 60)
print("2) .shape -> (linhas, colunas)")
print("=" * 60)
print(df.shape)

print("\n" + "=" * 60)
print("3) .dtypes -> o tipo que o pandas INFERIU para cada coluna")
print("=" * 60)
print(df.dtypes)

print("\n" + "=" * 60)
print("4) .info() -> tipos + contagem de valores NAO-nulos por coluna")
print("=" * 60)
df.info()

print("\n" + "=" * 60)
print("5) .describe() -> estatisticas SO das colunas numericas")
print("=" * 60)
print(df.describe())

print("\n" + "=" * 60)
print("6) O PROBLEMA: tentar somar a coluna 'preco'")
print("=" * 60)
try:
    total = df["preco"].sum()
    print("Soma de preco:", total)
except Exception as e:
    print("ERRO ao somar:", type(e).__name__, "-", e)
print("Tipo da coluna preco:", df["preco"].dtype)
print("Amostra de precos:", df["preco"].head(3).tolist())
