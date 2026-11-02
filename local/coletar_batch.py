"""Coleta local do The Batch: o site bloqueia os servidores do GitHub, mas não o computador do usuário.

Baixa o feed, grava entradas/the-batch.json (consumido pela rodada diária na nuvem) e
envia só esse arquivo ao repositório. Roda sozinho, agendado pelo systemd (ver local/README.md).
Uso manual de teste: python local/coletar_batch.py --sem-git
"""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import feedparser
from bs4 import BeautifulSoup

RAIZ = Path(__file__).resolve().parent.parent
FEED = "https://charonhub.deeplearning.ai/rss/"
SAIDA = RAIZ / "entradas/the-batch.json"
MAX_ITENS = 15
MAX_TEXTO = 6000


def coletar():
    feed = feedparser.parse(FEED)
    if not feed.entries:
        raise SystemExit("feed vazio ou inacessível; nada gravado")
    itens = []
    for e in feed.entries[:MAX_ITENS]:
        html = e["content"][0]["value"] if e.get("content") else e.get("summary", "")
        texto = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)[:MAX_TEXTO]
        slug = e.link.rstrip("/").split("/")[-1]
        itens.append({"url": f"https://www.deeplearning.ai/the-batch/{slug}/",  # endereço público do artigo
                      "titulo": e.title, "texto": texto, "data": e.get("published", "")})
    return {"atualizado": datetime.now(timezone.utc).isoformat(timespec="seconds"), "itens": itens}


def git(*args):
    return subprocess.run(["git", "-C", str(RAIZ), *args], check=True, capture_output=True, text=True)


def main():
    dados = coletar()
    SAIDA.parent.mkdir(exist_ok=True)
    SAIDA.write_text(json.dumps(dados, ensure_ascii=False, indent=2))
    print(f"{len(dados['itens'])} artigos gravados em {SAIDA}")
    if "--sem-git" in sys.argv:
        return
    # só este arquivo é versionado, mesmo que o resto da pasta esteja em edição
    git("pull", "--rebase", "--autostash")
    git("add", "entradas/the-batch.json")
    mudou = subprocess.run(["git", "-C", str(RAIZ), "diff", "--cached", "--quiet", "--",
                            "entradas/the-batch.json"]).returncode != 0
    if mudou:
        git("commit", "-m", "The Batch: coleta local", "--", "entradas/the-batch.json")
        git("push")
        print("enviado ao repositório")
    else:
        print("sem novidades")


if __name__ == "__main__":
    main()
