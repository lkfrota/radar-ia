"""Processa o feedback gravado pelas páginas (um arquivo JSON por clique em feedback/).

Cada arquivo: {"url", "tema", "fonte", "acao": "like" | "dislike" | "lido"}.
"""
import json
from pathlib import Path

PASSO = {"like": 0.10, "dislike": -0.15}  # dislike pesa mais: descartar é sinal mais forte
LIMITE = 0.5


def _ajusta(d, chave, delta):
    d[chave] = round(max(-LIMITE, min(LIMITE, d.get(chave, 0) + delta)), 3)


def processar(pasta, pesos, pendentes, vistos):
    """Aplica e apaga os arquivos de feedback. Devolve (pesos, pendentes, vistos)."""
    for f in sorted(Path(pasta).glob("*.json")):
        fb = json.loads(f.read_text())
        acao = fb["acao"]
        if acao in PASSO:
            _ajusta(pesos["temas"], fb["tema"], PASSO[acao])
            _ajusta(pesos["fontes"], fb["fonte"], PASSO[acao])
        if acao in ("lido", "dislike"):
            pendentes = [p for p in pendentes if p["url"] != fb["url"]]
            if fb["url"] not in vistos:
                vistos.append(fb["url"])
        f.unlink()
    return pesos, pendentes, vistos
