"""Gera um dataset sintetico de vendas (2000 linhas) para treinar ML de verdade.

A 'verdade' escondida que o modelo tera que descobrir:
  quantidade = base_da_categoria - 0.0015*preco + 0.8*avaliacao + sazonalidade(mes) + ruido
"""
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)  # semente fixa -> resultado reproduzivel
N = 2000

categorias = ["Eletronicos", "Acessorios", "Moveis", "Componentes", "Livros"]
base_categoria = {
    "Eletronicos": 4.0, "Acessorios": 9.0, "Moveis": 3.0,
    "Componentes": 5.0, "Livros": 11.0,
}
faixa_preco = {
    "Eletronicos": (800, 5000), "Acessorios": (30, 400), "Moveis": (300, 2500),
    "Componentes": (150, 3000), "Livros": (20, 120),
}

cat = rng.choice(categorias, size=N)
preco = np.array([rng.uniform(*faixa_preco[c]) for c in cat]).round(2)
avaliacao = np.clip(rng.normal(4.3, 0.5, N), 1, 5).round(1)
mes = rng.integers(1, 13, N)
# Sazonalidade: pico em novembro/dezembro (Black Friday / Natal)
sazonalidade = np.where(np.isin(mes, [11, 12]), 4.0, np.where(np.isin(mes, [1, 2]), -1.5, 0.0))

quantidade = (
    np.array([base_categoria[c] for c in cat])
    - 0.0015 * preco
    + 0.8 * avaliacao
    + sazonalidade
    + rng.normal(0, 1.0, N)          # ruido: o mundo nao e perfeito
)
quantidade = np.clip(np.round(quantidade), 1, None).astype(int)

df = pd.DataFrame({
    "data_venda": pd.to_datetime("2024-01-01") + pd.to_timedelta(rng.integers(0, 365, N), unit="D"),
    "categoria": cat,
    "preco": preco,
    "avaliacao": avaliacao,
    "mes": mes,
    "cliente_id": rng.integers(10000, 99999, N),
    "quantidade": quantidade,   # <- ALVO que vamos prever
})
df.to_csv("data/vendas_grande.csv", index=False)
print("Gerado data/vendas_grande.csv:", df.shape)
print(df.head())
