"""Rodada diária: feedback -> coleta -> triagem -> seleção -> redação -> HTML."""
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import coletar, montar, pesos as pesos_mod, pontuar

RAIZ = Path(__file__).resolve().parent.parent
MAX_DIAS_PENDENTE = 3
MAX_VISTOS = 1500


def _ler(rel):
    return json.loads((RAIZ / rel).read_text())


def _gravar(rel, dados):
    (RAIZ / rel).write_text(json.dumps(dados, ensure_ascii=False, indent=2))


def rodar():
    hoje = date.today().isoformat()
    fontes, perfil = _ler("config/fontes.json"), _ler("config/perfil.json")
    pesos, pendentes, vistos = _ler("estado/pesos.json"), _ler("estado/pendentes.json"), _ler("estado/vistos.json")

    pesos, pendentes, vistos = pesos_mod.processar(RAIZ / "feedback", pesos, pendentes, vistos)
    limite = (date.today() - timedelta(days=MAX_DIAS_PENDENTE)).isoformat()
    pendentes = [p for p in pendentes if p["dia"] > limite]

    itens, falhas = coletar.coletar_tudo(fontes)
    ja = set(vistos) | {p["url"] for p in pendentes}
    itens = [i for i in itens if i.url not in ja]
    pontuar.pontuar(itens, perfil)
    escolhidos = montar.selecionar(itens, pesos, set(vistos))

    textos = montar.redigir_lote(escolhidos)
    novos = [{"url": it.url, "fonte": it.fonte, "tema": it.tema, "tipo": it.tipo,
              "categoria": it.categoria, "nota": it.nota, **textos[it.url], "dia": hoje}
             for it in escolhidos if it.url in textos]
    for it in escolhidos:
        if it.url not in textos:
            print(f"sem redação (fica para amanhã): {it.url}", file=sys.stderr)

    # Pendentes (não marcados como lidos) ficam no topo por até MAX_DIAS_PENDENTE dias
    todos = [dict(p, pendente=True) for p in pendentes] + novos
    vistos += [n["url"] for n in novos]

    env = Environment(loader=FileSystemLoader(RAIZ / "templates"), autoescape=select_autoescape())
    agora = datetime.now(timezone.utc).astimezone().strftime("%d/%m/%Y %H:%M")
    (RAIZ / "docs/index.html").write_text(env.get_template("index.html").render(
        itens=todos, data=agora, falhas=falhas))
    (RAIZ / "docs/config.html").write_text(env.get_template("config.html").render())

    _gravar("estado/pesos.json", pesos)
    _gravar("estado/pendentes.json", [{k: v for k, v in t.items() if k != "pendente"} for t in todos])
    _gravar("estado/vistos.json", vistos[-MAX_VISTOS:])
    print(f"{len(novos)} novos, {len(pendentes)} pendentes, {len(falhas)} fontes com falha")


if __name__ == "__main__":
    rodar()
