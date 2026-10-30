"""Coleta candidatos das fontes configuradas.

Cada coletor devolve uma lista de Item. Falha em uma fonte nunca derruba a rodada:
o erro vai para o log e a fonte é pulada.
"""
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

import feedparser
import requests
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) radar-ia/0.1"}
TIMEOUT = 20
MAX_TEXTO = 6000  # caracteres de corpo enviados ao modelo por item


@dataclass
class Item:
    url: str
    titulo: str
    fonte: str
    tipo: str  # artigo | video | discussao
    texto: str = ""
    data: str = ""
    descoberta: bool = False  # veio de fonte de descoberta (alimenta a cota "fora do radar")

    def dict(self):
        return asdict(self)


def _get(url, headers=None, **kw):
    r = requests.get(url, headers={**UA, **(headers or {})}, timeout=TIMEOUT, **kw)
    r.raise_for_status()
    return r


def _texto_pagina(html):
    s = BeautifulSoup(html, "html.parser")
    for t in s(["script", "style", "nav", "footer", "header"]):
        t.decompose()
    return s, re.sub(r"\s+", " ", s.get_text(" ", strip=True))


def _artigo(url, fonte, descoberta=False):
    """Baixa uma página de artigo e extrai título, data e corpo."""
    html = _get(url).text
    s, corpo = _texto_pagina(html)
    meta = {m.get("property"): m.get("content") for m in s.find_all("meta") if m.get("property")}
    titulo = meta.get("og:title") or (s.title.string if s.title else url)
    return Item(url=url, titulo=titulo.strip(), fonte=fonte, tipo="artigo",
                texto=corpo[:MAX_TEXTO], data=meta.get("article:published_time", ""),
                descoberta=descoberta)


def coletar_rss(fonte, limite):
    feed = feedparser.parse(fonte["url"], request_headers=UA)
    itens = []
    for e in feed.entries[:limite]:
        texto = BeautifulSoup(e.get("summary", ""), "html.parser").get_text(" ", strip=True)
        itens.append(Item(e.link, e.title, fonte["nome"], "artigo", texto[:MAX_TEXTO],
                          e.get("published", "")))
    return itens


def coletar_youtube(fonte, limite):
    """O RSS do YouTube é instável (404/500 frequentes); lê os ids da página do canal
    (ordem = mais novos primeiro) e pega o título pelo oEmbed, que não exige chave."""
    html = _get(f"https://www.youtube.com/@{fonte['canal']}/videos",
                headers={"Accept-Language": "pt-BR"}).text
    ids = list(dict.fromkeys(re.findall(r'"videoId":"([A-Za-z0-9_-]{11})"', html)))[:limite]
    itens = []
    for vid in ids:
        url = f"https://www.youtube.com/watch?v={vid}"
        try:
            titulo = _get("https://www.youtube.com/oembed",
                          params={"url": url, "format": "json"}).json()["title"]
        except Exception as e:  # vídeo privado/removido
            print(f"  oembed falhou para {vid}: {e}", file=sys.stderr)
            continue
        itens.append(Item(url, titulo, fonte["nome"], "video"))
    return itens


def coletar_pagina(fonte, limite):
    """Fontes sem RSS: acha links na página-índice pelo padrão da config e lê cada artigo."""
    html = _get(fonte["url"]).text
    base = re.match(r"https?://[^/]+", fonte["url"]).group(0)
    links = re.findall(fonte["padrao_link"], html)
    links = list(dict.fromkeys(links))
    if fonte.get("ordem") == "numerica_desc":  # ex.: issue-368 > issue-367
        links.sort(key=lambda l: int(re.search(r"(\d+)/?$", l).group(1)), reverse=True)
    itens = []
    for l in links:
        if len(itens) >= limite:
            break
        try:
            it = _artigo(l if l.startswith("http") else base + l, fonte["nome"])
        except Exception as e:
            print(f"  artigo falhou {l}: {e}", file=sys.stderr)
            continue
        # páginas de categoria do índice (ex.: /news/announcements) não têm data de publicação
        if not it.data:
            continue
        itens.append(it)
    return itens


def coletar_hackernews(fonte, limite):
    ids = _get("https://hacker-news.firebaseio.com/v0/topstories.json").json()[:60]
    itens = []
    for i in ids:
        d = _get(f"https://hacker-news.firebaseio.com/v0/item/{i}.json").json() or {}
        if d.get("url") and d.get("score", 0) >= fonte.get("score_min", 150):
            itens.append(Item(d["url"], d.get("title", ""), fonte["nome"], "discussao",
                              descoberta=True))
        if len(itens) >= limite:
            break
    return itens


def coletar_hf_papers(fonte, limite):
    dados = _get("https://huggingface.co/api/daily_papers").json()
    itens = []
    for d in dados[:limite]:
        p = d["paper"]
        itens.append(Item(f"https://huggingface.co/papers/{p['id']}", p["title"], fonte["nome"],
                          "artigo", (p.get("summary") or "")[:MAX_TEXTO],
                          p.get("publishedAt", ""), descoberta=True))
    return itens


COLETORES = {"rss": coletar_rss, "youtube": coletar_youtube, "pagina": coletar_pagina,
             "hackernews": coletar_hackernews, "hf_papers": coletar_hf_papers}


def coletar_tudo(fontes):
    """Devolve (itens, falhas). Fontes com ativo=false são ignoradas."""
    itens, falhas = [], []
    for f in fontes:
        if not f.get("ativo", True):
            continue
        try:
            novos = COLETORES[f["tipo"]](f, f.get("limite", 5))
            print(f"{f['nome']}: {len(novos)} itens")
            itens += novos
        except Exception as e:
            print(f"{f['nome']}: FALHOU ({e})", file=sys.stderr)
            falhas.append({"fonte": f["nome"], "erro": str(e)})
    return itens, falhas


if __name__ == "__main__":
    fontes = json.loads(Path(sys.argv[1] if len(sys.argv) > 1 else "config/fontes.json").read_text())
    itens, falhas = coletar_tudo(fontes)
    print(f"\n{len(itens)} itens, {len(falhas)} falhas")
    for i in itens[:40]:
        print(f"- [{i.fonte}] {i.titulo[:80]}")
