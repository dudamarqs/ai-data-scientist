/**
 * Frontend do AI Data Scientist.
 *
 * Nao ha framework: so fetch + DOM. O servidor ja entrega tudo pronto
 * (perfil, tabela, figuras do Plotly em JSON) -- o navegador so desenha.
 */

const $ = (id) => document.getElementById(id);

let datasetId = null;
let enviando = false;

/* ---------------- Upload ---------------- */

const dropzone = $("dropzone");
const inputArquivo = $("input-arquivo");

dropzone.addEventListener("click", () => inputArquivo.click());
$("btn-escolher").addEventListener("click", (e) => {
  e.stopPropagation();
  inputArquivo.click();
});
inputArquivo.addEventListener("change", () => {
  if (inputArquivo.files[0]) enviarArquivo(inputArquivo.files[0]);
});

["dragenter", "dragover"].forEach((evento) =>
  dropzone.addEventListener(evento, (e) => {
    e.preventDefault();
    dropzone.classList.add("arrastando");
  })
);
["dragleave", "drop"].forEach((evento) =>
  dropzone.addEventListener(evento, (e) => {
    e.preventDefault();
    dropzone.classList.remove("arrastando");
  })
);
dropzone.addEventListener("drop", (e) => {
  const arquivo = e.dataTransfer.files[0];
  if (arquivo) enviarArquivo(arquivo);
});

async function enviarArquivo(arquivo) {
  const erro = $("erro-upload");
  erro.hidden = true;
  dropzone.querySelector("h2").textContent = "Analisando…";

  const formulario = new FormData();
  formulario.append("arquivo", arquivo);

  try {
    const resposta = await fetch("/datasets", { method: "POST", body: formulario });
    const corpo = await resposta.json();
    if (!resposta.ok) throw new Error(corpo.detail || "Falha ao enviar o arquivo.");

    datasetId = corpo.dataset_id;
    mostrarWorkspace(corpo);
    carregarTabela();
    carregarGraficos();
  } catch (e) {
    erro.textContent = e.message;
    erro.hidden = false;
    dropzone.querySelector("h2").textContent = "Arraste seu CSV aqui";
  }
}

/* ---------------- Painel de dados ---------------- */

function mostrarWorkspace(dados) {
  $("tela-upload").hidden = true;
  $("tela-dados").hidden = false;

  $("cartoes").innerHTML = `
    ${cartao(dados.linhas.toLocaleString("pt-BR"), "linhas")}
    ${cartao(dados.colunas, "colunas")}
    ${cartao(dados.duplicatas_removidas, "duplicatas removidas")}
  `;

  $("chips").innerHTML = Object.entries(dados.perfil)
    .map(
      ([coluna, tipo]) =>
        `<span class="chip" data-tipo="${tipo}">${coluna}<span class="tipo">${tipo}</span></span>`
    )
    .join("");
}

const cartao = (valor, rotulo) =>
  `<div class="cartao"><div class="valor">${valor}</div><div class="rotulo">${rotulo}</div></div>`;

async function carregarTabela() {
  const dados = await (await fetch(`/datasets/${datasetId}/preview`)).json();

  const cabecalho = `<thead><tr>${dados.colunas
    .map((c) => `<th>${c}</th>`)
    .join("")}</tr></thead>`;

  const corpo = dados.linhas
    .map(
      (linha) =>
        `<tr>${dados.colunas
          .map((c) => {
            const valor = linha[c];
            return valor === null || valor === undefined
              ? `<td class="nulo">vazio</td>`
              : `<td>${valor}</td>`;
          })
          .join("")}</tr>`
    )
    .join("");

  $("tabela").innerHTML = cabecalho + `<tbody>${corpo}</tbody>`;
}

async function carregarGraficos() {
  const alvo = $("graficos");
  try {
    const dados = await (await fetch(`/datasets/${datasetId}/graficos`)).json();
    alvo.innerHTML = "";

    if (!dados.graficos.length) {
      alvo.innerHTML = `<p class="carregando">Sem colunas numéricas para plotar.</p>`;
      return;
    }

    dados.graficos.forEach((g, i) => {
      const caixa = document.createElement("div");
      caixa.className = "grafico";
      caixa.id = `grafico-${i}`;
      alvo.appendChild(caixa);
      Plotly.newPlot(caixa, g.figura.data, g.figura.layout, {
        responsive: true,
        displayModeBar: false,
      });
    });
  } catch {
    alvo.innerHTML = `<p class="carregando">Não foi possível gerar os gráficos.</p>`;
  }
}

/* ---------------- Abas ---------------- */

document.querySelectorAll(".aba").forEach((aba) =>
  aba.addEventListener("click", () => {
    document.querySelectorAll(".aba").forEach((a) => a.classList.remove("ativa"));
    aba.classList.add("ativa");
    const alvo = aba.dataset.aba;
    $("painel-tabela").hidden = alvo !== "tabela";
    $("painel-graficos").hidden = alvo !== "graficos";
    // O Plotly precisa recalcular o tamanho quando a aba fica visível.
    if (alvo === "graficos") window.dispatchEvent(new Event("resize"));
  })
);

$("btn-trocar").addEventListener("click", () => location.reload());

/* ---------------- Chat ---------------- */

const mensagens = $("mensagens");

document.addEventListener("click", (e) => {
  if (e.target.classList.contains("sugestao")) {
    $("input-pergunta").value = e.target.textContent;
    $("form-chat").requestSubmit();
  }
});

$("form-chat").addEventListener("submit", async (e) => {
  e.preventDefault();
  if (enviando) return;

  const campo = $("input-pergunta");
  const pergunta = campo.value.trim();
  if (pergunta.length < 3) return;

  campo.value = "";
  adicionarMensagem(pergunta, "user");

  enviando = true;
  $("btn-enviar").disabled = true;
  const pensando = adicionarPensando();

  try {
    const resposta = await fetch(`/datasets/${datasetId}/perguntar`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ texto: pergunta }),
    });
    const corpo = await resposta.json();
    pensando.remove();

    if (!resposta.ok) {
      adicionarMensagem(corpo.detail || "Erro ao consultar o modelo.", "bot", [], true);
      return;
    }
    adicionarMensagem(corpo.resposta, "bot", corpo.bastidores);
  } catch {
    pensando.remove();
    adicionarMensagem("Não consegui falar com o servidor.", "bot", [], true);
  } finally {
    enviando = false;
    $("btn-enviar").disabled = false;
  }
});

function adicionarMensagem(texto, autor, bastidores = [], ehErro = false) {
  const div = document.createElement("div");
  div.className = `msg ${autor}` + (ehErro ? " erro-msg" : "");
  div.innerHTML = formatar(texto);

  // OS BASTIDORES: a prova de que o número não foi inventado pelo LLM.
  if (bastidores.length) {
    const detalhes = document.createElement("details");
    detalhes.className = "bastidores";
    detalhes.innerHTML =
      `<summary>Bastidores — ${bastidores.length} ferramenta(s) executada(s) em Python</summary>` +
      bastidores
        .map(
          (b) => `
        <div class="passo">
          <div class="rotulo-passo">
            O LLM pediu: <code>${b.ferramenta}(${JSON.stringify(b.argumentos)})</code>
          </div>
          <div class="rotulo-passo">O Python calculou e devolveu:</div>
          <pre>${escapar(b.resultado)}</pre>
        </div>`
        )
        .join("");
    div.appendChild(detalhes);
  }

  mensagens.appendChild(div);
  mensagens.scrollTop = mensagens.scrollHeight;
  return div;
}

function adicionarPensando() {
  const div = document.createElement("div");
  div.className = "msg bot";
  div.innerHTML = `<div class="pensando"><span></span><span></span><span></span></div>`;
  mensagens.appendChild(div);
  mensagens.scrollTop = mensagens.scrollHeight;
  return div;
}

/** Markdown mínimo: **negrito**, `código` e parágrafos. */
function formatar(texto) {
  return escapar(texto)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`(.+?)`/g, "<code>$1</code>")
    .split(/\n{2,}/)
    .map((p) => `<p>${p.replace(/\n/g, "<br>")}</p>`)
    .join("");
}

/** Nunca injete texto de terceiros como HTML sem escapar (previne XSS). */
function escapar(texto) {
  const div = document.createElement("div");
  div.textContent = texto;
  return div.innerHTML;
}
