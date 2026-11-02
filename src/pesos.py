"""Processa o feedback gravado pelas páginas (um arquivo JSON por clique em feedback/).

Cada arquivo: {"url", "tema", "fonte", "acao"}. Toda ação dispensa o item da página.
O tema recebe o sinal inteiro; a fonte, uma fração (ver EFEITOS).
"""
import json
from pathlib import Path

LIMITE = 0.5
# A fonte nunca é julgada por um clique próprio: um item ruim não faz uma fonte ruim. Ela recebe só
# uma fração do sinal de cada reação, e a qualidade real aparece no acúmulo (muitos "fora do foco"
# derrubam a fonte aos poucos; muitos "quero mais" a sobem).
EFEITOS = {  # variação de peso do tema e/ou da fonte
    "quero_mais": {"tema": 0.15, "fonte": 0.05},
    "util": {"tema": 0.08, "fonte": 0.03},
    "fora_foco": {"tema": -0.15, "fonte": -0.05},
    "ja_conhecia": {},  # não mexe nos pesos: conta como "conhecido" (reduz o valor de novidade do tema)
    "fonte_fraca": {"fonte": -0.05},  # botão removido em 2026-11-02; mantido só para cliques já gravados
}
LEGADO = {"like": "util", "dislike": "fora_foco", "lido": "ja_conhecia"}  # arquivos da 1ª versão da página


def _ajusta(d, chave, delta):
    d[chave] = round(max(-LIMITE, min(LIMITE, d.get(chave, 0) + delta)), 3)


def processar(pasta, pesos, pendentes, vistos):
    """Aplica e apaga os arquivos de feedback. Devolve (pesos, pendentes, vistos)."""
    pesos.setdefault("conhecido", {})
    for f in sorted(Path(pasta).glob("*.json")):
        fb = json.loads(f.read_text())
        acao = LEGADO.get(fb["acao"], fb["acao"])
        ef = EFEITOS.get(acao)
        if ef is None:
            f.unlink()
            continue
        if "tema" in ef:
            _ajusta(pesos["temas"], fb["tema"], ef["tema"])
        if "fonte" in ef:
            _ajusta(pesos["fontes"], fb["fonte"], ef["fonte"])
        if acao == "ja_conhecia" and fb["acao"] != "lido":  # o "lido" legado não diz nada sobre novidade
            pesos["conhecido"][fb["tema"]] = pesos["conhecido"].get(fb["tema"], 0) + 1
        pendentes = [p for p in pendentes if p["url"] != fb["url"]]
        if fb["url"] not in vistos:
            vistos.append(fb["url"])
        f.unlink()
    return pesos, pendentes, vistos
