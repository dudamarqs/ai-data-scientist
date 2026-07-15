/**
 * Frontend do AI Data Scientist.
 *
 * Sem framework: fetch + DOM. O servidor entrega tudo pronto (perfil, tabela,
 * figuras do Plotly em JSON) -- o navegador so desenha.
 */

const $ = (id) => document.getElementById(id);

let datasetId = null;
let enviando = false;

/* ===================== TEMA (claro / escuro) ===================== */

const CHAVE_TEMA = "ads-tema";

function temaAtual() {
  return document.documentElement.dataset.tema;
}

function aplicarTema(tema) {
  document.documentElement.dataset.tema = tema;
  localStorage.setItem(CHAVE_TEMA, tema);
  // O icone mostra para ONDE voce vai, nao onde esta.
  $("btn-tema").innerHTML =
    tema === "escuro"
      ? '<i class="bi bi-sun"></i>'
      : '<i class="bi bi-moon-stars"></i>';
}

// Preferencia salva > preferencia do sistema operacional > claro.
aplicarTema(
  localStorage.getItem(CHAVE_TEMA) ||
    (matchMedia("(prefers-color-scheme: dark)").matches ? "escuro" : "claro")
);

$("btn-tema").addEventListener("click", () => {
  aplicarTema(temaAtual() === "escuro" ? "claro" : "escuro");
  // Os graficos sao gerados no servidor COM o tema -> precisam ser refeitos.
  if (datasetId && !$("painel-graficos").hidden) carregarGraficos();
  else graficosCarregados = false;
});

/* ===================== UPLOAD ===================== */

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

["dragenter", "dragover"].forEach((ev) =>
  dropzone.addEventListener(ev, (e) => {
    e.preventDefault();
    dropzone.classList.add("arrastando");
  })
);
["dragleave", "drop"].forEach((ev) =>
  dropzone.addEventListener(ev, (e) => {
    e.preventDefault();
    dropzone.classList.remove("arrastando");
  })
);
dropzone.addEventListener("drop", (e) => {
  const arquivo = e.dataTransfer.files[0];
  if (arquivo) enviarArquivo(arquivo);
});

async function enviarArquivo(arquivo) {
  const alerta = $("erro-upload");
  alerta.hidden = true;
  dropzone.querySelector(".dropzone-titulo").textContent = "Analisando...";

  const formulario = new FormData();
  formulario.append("arquivo", arquivo);

  try {
    const resposta = await fetch("/datasets", { method: "POST", body: formulario });
    const corpo = await resposta.json();
    if (!resposta.ok) throw new Error(corpo.detail || "Falha ao enviar o arquivo.");

    datasetId = corpo.dataset_id;
    abrirChat(corpo, arquivo.name);
  } catch (e) {
    alerta.querySelector("span").textContent = e.message;
    alerta.hidden = false;
    dropzone.querySelector(".dropzone-titulo").textContent = "Arraste o arquivo aqui";
  }
}

function abrirChat(dados, nomeArquivo) {
  $("tela-upload").hidden = true;
  $("tela-chat").hidden = false;

  $("nome-arquivo").textContent = nomeArquivo;
  $("chip-arquivo").hidden = false;
  $("btn-painel").hidden = false;
  $("btn-novo").hidden = false;

  $("cartoes").innerHTML =
    cartao(dados.linhas.toLocaleString("pt-BR"), "linhas") +
    cartao(dados.colunas, "colunas") +
    cartao(dados.duplicatas_removidas, "duplicatas");

  const icones = {
    moeda: "bi-cash-coin",
    data: "bi-calendar3",
    identificador: "bi-key",
    categoria: "bi-tag",
    numerico: "bi-123",
    texto: "bi-fonts",
  };
  $("chips").innerHTML = Object.entries(dados.perfil)
    .map(
      ([coluna, tipo]) => `
      <span class="chip" data-tipo="${tipo}">
        <i class="bi ${icones[tipo] || "bi-question"}"></i>
        ${escapar(coluna)}<span class="tipo">${tipo}</span>
      </span>`
    )
    .join("");

  carregarTabela();
  $("input-pergunta").focus();
}

const cartao = (valor, rotulo) =>
  `<div class="cartao"><div class="valor">${valor}</div><div class="rotulo">${rotulo}</div></div>`;

$("btn-novo").addEventListener("click", () => location.reload());

/* ===================== PAINEL DESLIZANTE ===================== */

let graficosCarregados = false;

function abrirPainel() {
  $("painel").hidden = false;
  $("cortina").hidden = false;
}
function fecharPainel() {
  $("painel").hidden = true;
  $("cortina").hidden = true;
}

$("btn-painel").addEventListener("click", abrirPainel);
$("btn-fechar-painel").addEventListener("click", fecharPainel);
$("cortina").addEventListener("click", fecharPainel);
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !$("painel").hidden) fecharPainel();
});

document.querySelectorAll(".aba").forEach((aba) =>
  aba.addEventListener("click", () => {
    document.querySelectorAll(".aba").forEach((a) => a.classList.remove("ativa"));
    aba.classList.add("ativa");

    const alvo = aba.dataset.aba;
    $("painel-perfil").hidden = alvo !== "perfil";
    $("painel-tabela").hidden = alvo !== "tabela";
    $("painel-graficos").hidden = alvo !== "graficos";

    if (alvo === "graficos") {
      if (!graficosCarregados) carregarGraficos();
      else window.dispatchEvent(new Event("resize")); // Plotly recalcula o tamanho
    }
  })
);

async function carregarTabela() {
  const dados = await (await fetch(`/datasets/${datasetId}/preview?linhas=100`)).json();

  const cabecalho = `<thead><tr>${dados.colunas
    .map((c) => `<th>${escapar(c)}</th>`)
    .join("")}</tr></thead>`;

  const corpo = dados.linhas
    .map(
      (linha) =>
        `<tr>${dados.colunas
          .map((c) => {
            const valor = linha[c];
            return valor === null || valor === undefined
              ? `<td class="nulo">vazio</td>`
              : `<td>${escapar(String(valor))}</td>`;
          })
          .join("")}</tr>`
    )
    .join("");

  $("tabela").innerHTML = cabecalho + `<tbody>${corpo}</tbody>`;

  // Legenda honesta: quantas linhas estao a mostra, de quantas no total.
  const mostradas = dados.linhas.length;
  const total = dados.total_linhas;
  $("legenda-tabela").textContent =
    mostradas < total
      ? `Mostrando as primeiras ${mostradas} de ${total.toLocaleString("pt-BR")} linhas`
      : `Mostrando todas as ${total.toLocaleString("pt-BR")} linhas`;
}

async function carregarGraficos() {
  const alvo = $("graficos");
  alvo.innerHTML = `<p class="nota-centro"><i class="bi bi-hourglass-split"></i> Gerando gráficos...</p>`;

  try {
    const url = `/datasets/${datasetId}/graficos?tema=${temaAtual()}`;
    const dados = await (await fetch(url)).json();
    alvo.innerHTML = "";

    if (!dados.graficos.length) {
      alvo.innerHTML = `<p class="nota-centro"><i class="bi bi-slash-circle"></i> Sem colunas numéricas para plotar.</p>`;
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
    graficosCarregados = true;
  } catch {
    alvo.innerHTML = `<p class="nota-centro"><i class="bi bi-exclamation-triangle"></i> Não foi possível gerar os gráficos.</p>`;
  }
}

/* ===================== CHAT ===================== */

const mensagens = $("mensagens");

document.addEventListener("click", (e) => {
  const sugestao = e.target.closest(".sugestao");
  if (!sugestao) return;
  $("input-pergunta").value = sugestao.textContent.trim();
  $("form-chat").requestSubmit();
});

$("form-chat").addEventListener("submit", async (e) => {
  e.preventDefault();
  if (enviando) return;

  const campo = $("input-pergunta");
  const pergunta = campo.value.trim();
  if (pergunta.length < 3) return;

  campo.value = "";
  adicionarUsuario(pergunta);

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
      adicionarAssistente(corpo.detail || "Erro ao consultar o modelo.", [], true);
      return;
    }
    adicionarAssistente(corpo.resposta, corpo.bastidores);
  } catch {
    pensando.remove();
    adicionarAssistente("Não consegui falar com o servidor.", [], true);
  } finally {
    enviando = false;
    $("btn-enviar").disabled = false;
    campo.focus();
  }
});

function adicionarUsuario(texto) {
  const artigo = document.createElement("article");
  artigo.className = "msg usuario";
  artigo.innerHTML = `<div class="balao">${escapar(texto)}</div>`;
  mensagens.appendChild(artigo);
  rolar();
}

function adicionarAssistente(texto, bastidores = [], ehErro = false) {
  const artigo = document.createElement("article");
  artigo.className = "msg assistente" + (ehErro ? " erro" : "");
  artigo.innerHTML = `
    <span class="avatar"><i class="bi bi-bar-chart-line-fill"></i></span>
    <div class="balao">${formatar(texto)}</div>`;

  // BASTIDORES: a prova de que o numero saiu do Python, nao do modelo.
  if (bastidores.length) {
    const detalhes = document.createElement("details");
    detalhes.className = "bastidores";
    detalhes.innerHTML =
      `<summary>
         <i class="bi bi-tools"></i>
         Auditoria: ${bastidores.length} ferramenta(s) executada(s) em Python
         <i class="bi bi-chevron-right seta"></i>
       </summary>` +
      bastidores
        .map(
          (b) => `
        <div class="passo">
          <div class="linha pedido">
            <i class="bi bi-cpu"></i>
            O modelo pediu <code>${escapar(b.ferramenta)}(${escapar(
            JSON.stringify(b.argumentos)
          )})</code>
          </div>
          <div class="linha">
            <i class="bi bi-terminal"></i> O Python calculou e devolveu:
          </div>
          <pre>${escapar(b.resultado)}</pre>
        </div>`
        )
        .join("");
    artigo.querySelector(".balao").appendChild(detalhes);
  }

  mensagens.appendChild(artigo);
  rolar();
}

function adicionarPensando() {
  const artigo = document.createElement("article");
  artigo.className = "msg assistente";
  artigo.innerHTML = `
    <span class="avatar"><i class="bi bi-bar-chart-line-fill"></i></span>
    <div class="balao">
      <div class="pensando"><span></span><span></span><span></span></div>
    </div>`;
  mensagens.appendChild(artigo);
  rolar();
  return artigo;
}

const rolar = () => (mensagens.scrollTop = mensagens.scrollHeight);

/** Markdown minimo: **negrito**, `codigo`, listas simples e paragrafos. */
function formatar(texto) {
  return escapar(texto)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`(.+?)`/g, "<code>$1</code>")
    .replace(/^#{1,6}\s*(.+)$/gm, "<strong>$1</strong>")
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
