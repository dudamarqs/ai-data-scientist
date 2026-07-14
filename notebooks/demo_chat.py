"""
Demo ao vivo: conversa com os dados, mostrando os bastidores.

Instrumentamos a CaixaDeFerramentas para IMPRIMIR cada chamada que o LLM faz
e cada resultado que o NOSSO codigo devolve. Assim da para ver, na pratica,
que o LLM nunca calcula -- ele so orquestra.

    .venv\\Scripts\\python.exe notebooks/demo_chat.py
"""
from app.core.pipeline import preparar
from app.llm import CaixaDeFerramentas, OrquestradorLLM, criar_cliente, descrever_dataset


class CaixaEspiada(CaixaDeFerramentas):
    """Mesma caixa de ferramentas, mas narrando o que acontece."""

    def executar(self, nome: str, argumentos: dict) -> str:
        print(f"\n  [MAESTRO] O LLM PEDIU a ferramenta: {nome}({argumentos})")
        resultado = super().executar(nome, argumentos)
        print("  [ORQUESTRA] NOSSO CODIGO (pandas/sklearn) calculou e devolveu:")
        for linha in resultado.splitlines()[:8]:
            print(f"       {linha}")
        if len(resultado.splitlines()) > 8:
            print("       ...")
        return resultado


def main() -> None:
    print("=" * 70)
    print("1) PIPELINE: ingestao -> profiling -> qualidade")
    print("=" * 70)
    dataset = preparar("data/vendas_grande.csv")
    print(f"   {len(dataset.df)} linhas, {len(dataset.df.columns)} colunas")
    print(f"   duplicatas removidas: {dataset.duplicatas_removidas}")
    print(f"   perfil: {[(c, t.value) for c, t in dataset.perfil.items()]}")

    cliente, modelo = criar_cliente()
    print(f"\n   Provedor ativo: {type(cliente).__name__} | modelo: {modelo}")

    orquestrador = OrquestradorLLM(
        ferramentas=CaixaEspiada(dataset.df, dataset.perfil),
        contexto_dataset=descrever_dataset(dataset.df, dataset.perfil),
        cliente=cliente,
        modelo=modelo,
    )

    perguntas = [
        "Qual o preco tipico dos produtos?",
        "O que mais influencia a quantidade vendida?",
    ]

    for pergunta in perguntas:
        print("\n" + "=" * 70)
        print(f"PERGUNTA: {pergunta}")
        print("=" * 70)
        resposta = orquestrador.perguntar(pergunta)
        print(f"\n  >>> RESPOSTA FINAL:\n\n{resposta}\n")


if __name__ == "__main__":
    main()
