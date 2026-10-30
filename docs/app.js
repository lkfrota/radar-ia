// Páginas estáticas que gravam no repositório via API de conteúdo do GitHub.
// Token fine-grained fica só no localStorage deste navegador.
const REPO = "lkfrota/radar-ia";
const API = `https://api.github.com/repos/${REPO}/contents/`;

const guardar = (k, v) => { try { localStorage.setItem(k, v); } catch (e) {} };
const ler = (k) => { try { return localStorage.getItem(k); } catch (e) { return null; } };
const b64 = (s) => btoa(unescape(encodeURIComponent(s)));
const deb64 = (s) => decodeURIComponent(escape(atob(s.replace(/\n/g, ""))));

async function gh(caminho, opts = {}) {
  const r = await fetch(API + caminho, {
    ...opts,
    headers: { Accept: "application/vnd.github+json", Authorization: `Bearer ${ler("token") || ""}`, ...(opts.headers || {}) },
  });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}

async function gravarArquivo(caminho, conteudo, sha) {
  return gh(caminho, { method: "PUT", body: JSON.stringify({ message: `radar: ${caminho}`, content: b64(conteudo), ...(sha ? { sha } : {}) }) });
}

// ---------- página do dia ----------
function iniciarDigest() {
  const estado = JSON.parse(ler("estado-itens") || "{}");
  const salvar = () => guardar("estado-itens", JSON.stringify(estado));

  document.querySelectorAll("article").forEach((art) => {
    const url = art.dataset.url;
    const s = (estado[url] ||= {});
    const marcar = () => {
      art.classList.toggle("lido", !!s.lido);
      art.querySelector(".like").classList.toggle("on", s.voto === "like");
      art.querySelector(".dislike").classList.toggle("on", s.voto === "dislike");
      art.querySelector("input[data-acao=lido]").checked = !!s.lido;
    };
    marcar();

    const enviar = async (acao) => {
      const corpo = { url, tema: art.dataset.tema, fonte: art.dataset.fonte, acao };
      try {
        await gravarArquivo(`feedback/${Date.now()}-${Math.random().toString(36).slice(2, 7)}.json`, JSON.stringify(corpo));
      } catch (e) {
        alert("Não consegui gravar o feedback (" + e.message + "). Confira o token em Configurar.");
      }
    };

    art.querySelectorAll("button[data-acao]").forEach((b) => b.addEventListener("click", () => {
      const acao = b.dataset.acao;
      if (s.voto === acao) return;
      s.voto = acao; salvar(); marcar(); enviar(acao);
    }));
    art.querySelector("input[data-acao=lido]").addEventListener("change", (e) => {
      s.lido = e.target.checked; salvar(); marcar();
      if (s.lido) enviar("lido");
    });
  });
}

// ---------- página de configuração ----------
async function iniciarConfig() {
  const $ = (id) => document.getElementById(id);
  const status = (t) => ($("status").textContent = t);
  $("token").value = ler("token") || "";
  $("salvar-token").onclick = () => { guardar("token", $("token").value.trim()); status("Token guardado neste navegador."); };

  const dados = { fontes: null, perfil: null };
  const sha = {};
  try {
    for (const [k, f] of [["fontes", "config/fontes.json"], ["perfil", "config/perfil.json"]]) {
      const r = await fetch(`https://api.github.com/repos/${REPO}/contents/${f}`, { headers: { Accept: "application/vnd.github+json" } });
      if (!r.ok) throw new Error(r.status);
      const j = await r.json();
      sha[k] = j.sha; dados[k] = JSON.parse(deb64(j.content));
    }
  } catch (e) { return status("Não consegui carregar a configuração (" + e.message + ")."); }
  status("Configuração carregada. Alterações só valem depois de “Gravar”.");

  const lista = (ul, arr, rotulo, extra) => {
    ul.innerHTML = "";
    arr.forEach((x, i) => {
      const li = document.createElement("li"); li.className = "linha";
      li.innerHTML = `<span></span>`;
      li.firstChild.textContent = rotulo(x);
      if (extra) extra(li, x);
      const b = document.createElement("button"); b.textContent = "remover";
      b.onclick = () => { arr.splice(i, 1); render(); };
      li.append(b); ul.append(li);
    });
  };
  const render = () => {
    lista($("fontes"), dados.fontes, (f) => f.nome + (f.tipo === "youtube" ? " (YouTube)" : ""), (li, f) => {
      const c = document.createElement("input"); c.type = "checkbox"; c.checked = f.ativo !== false;
      c.title = "ativa"; c.onchange = () => { f.ativo = c.checked; }; li.prepend(c);
    });
    lista($("interesses"), dados.perfil.interesses, (x) => x);
    lista($("nao_interesses"), dados.perfil.nao_interesses, (x) => x);
  };
  render();

  $("add-fonte").onclick = () => {
    const nome = $("nova-nome").value.trim(), ref = $("nova-ref").value.trim();
    if (!nome || !ref) return;
    dados.fontes.push($("nova-tipo").value === "youtube"
      ? { nome: nome + " (YouTube)", tipo: "youtube", canal: ref.replace(/^@/, ""), limite: 4 }
      : { nome, tipo: "rss", url: ref, limite: 5 });
    $("nova-nome").value = $("nova-ref").value = ""; render();
  };
  $("add-interesse").onclick = () => { const v = $("novo-interesse").value.trim(); if (v) { dados.perfil.interesses.push(v); $("novo-interesse").value = ""; render(); } };
  $("add-nao").onclick = () => { const v = $("novo-nao").value.trim(); if (v) { dados.perfil.nao_interesses.push(v); $("novo-nao").value = ""; render(); } };

  $("gravar").onclick = async () => {
    try {
      const r1 = await gravarArquivo("config/fontes.json", JSON.stringify(dados.fontes, null, 2), sha.fontes);
      const r2 = await gravarArquivo("config/perfil.json", JSON.stringify(dados.perfil, null, 2), sha.perfil);
      sha.fontes = r1.content.sha; sha.perfil = r2.content.sha;
      status("Gravado. Vale a partir da próxima rodada.");
    } catch (e) { status("Falha ao gravar (" + e.message + "). Confira o token."); }
  };
}

document.addEventListener("DOMContentLoaded", () => {
  if (document.getElementById("fontes")) iniciarConfig(); else iniciarDigest();
});
