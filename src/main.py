"""Rodada diária: feedback -> coleta -> triagem -> seleção -> redação -> HTML."""
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import coletar, montar, pesos as pesos_mod, pontuar

RAIZ = Path(__file__).resolve().parent.parent
MAX_DIAS_PENDENTE = 3
MAX_PAGINA = 15  # teto da página (~10-15 min de leitura): itens de menor nota saem para dar vez aos novos
MAX_VISTOS = 1500
MAX_TENTATIVAS = 3  # rodadas por dia quando a triagem falha (o workflow é acionado 3 vezes ao dia)


def _ler(rel):
    return json.loads((RAIZ / rel).read_text())


def _gravar(rel, dados):
    (RAIZ / rel).write_text(json.dumps(dados, ensure_ascii=False, indent=2))


def precisa_rodar(registro, hoje):
    """Com --se-preciso: roda se o dia é outro, ou se a triagem de hoje falhou e ainda há tentativa.
    Assim os 3 acionamentos diários dão no máximo 1 rodada bem-sucedida por dia."""
    if registro.get("dia") != hoje:
        return True
    return not registro.get("triagem_ok") and registro.get("tentativa", 0) < MAX_TENTATIVAS


def rodar(se_preciso=False):
    hoje = date.today().isoformat()
    caminho = RAIZ / "estado/rodada.json"
    registro = json.loads(caminho.read_text()) if caminho.exists() else {}
    if se_preciso and not precisa_rodar(registro, hoje):
        print(f"rodada de {hoje} dispensada: {registro}")
        return
    tentativa = registro.get("tentativa", 0) + 1 if registro.get("dia") == hoje else 1
    fontes, perfil = _ler("config/fontes.json"), _ler("config/perfil.json")
    pesos, pendentes, vistos = _ler("estado/pesos.json"), _ler("estado/pendentes.json"), _ler("estado/vistos.json")

    pesos, pendentes, vistos = pesos_mod.processar(RAIZ / "feedback", pesos, pendentes, vistos)
    limite = (date.today() - timedelta(days=MAX_DIAS_PENDENTE)).isoformat()
    pendentes = [p for p in pendentes if p["dia"] > limite]

    itens, falhas = coletar.coletar_tudo(fontes)
    ja = set(vistos) | {p["url"] for p in pendentes}
    itens = [i for i in itens if i.url not in ja]
    n_coletados = len(itens)
    itens = pontuar.pontuar(itens, perfil)
    # ok se pontuou algo (falha parcial de um lote não justifica repetir) ou se não havia o que pontuar
    triagem_ok = bool(itens) or n_coletados == 0
    falhas += [{"fonte": f"triagem do Gemini indisponível ({a})", "erro": a} for a in pontuar.ADIADOS]
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
    # o teto vale para o conjunto: velhos e novos disputam por nota. Quem sai continua em
    # `vistos` e não volta.
    todos = sorted(todos, key=lambda t: t["nota"], reverse=True)[:MAX_PAGINA]
    vistos += [n["url"] for n in novos]

    env = Environment(loader=FileSystemLoader(RAIZ / "templates"), autoescape=select_autoescape())
    agora = datetime.now(timezone.utc).astimezone().strftime("%d/%m/%Y %H:%M")
    if triagem_ok:
        aviso = ""
    elif tentativa < MAX_TENTATIVAS:
        aviso = "Triagem indisponível; nova tentativa automática mais tarde."
    else:
        aviso = "Triagem indisponível em todas as tentativas de hoje; os itens novos ficam para amanhã."
    (RAIZ / "docs/index.html").write_text(env.get_template("index.html").render(
        itens=todos, data=agora, falhas=falhas, aviso_triagem=aviso))
    (RAIZ / "docs/config.html").write_text(env.get_template("config.html").render())

    _gravar("estado/pesos.json", pesos)
    _gravar("estado/pendentes.json", [{k: v for k, v in t.items() if k != "pendente"} for t in todos])
    _gravar("estado/vistos.json", vistos[-MAX_VISTOS:])
    _gravar("estado/rodada.json", {"dia": hoje, "hora": datetime.now(timezone.utc).strftime("%H:%M"),
                                   "triagem_ok": triagem_ok, "tentativa": tentativa})
    print(f"{len(novos)} novos, {len(pendentes)} pendentes, {len(falhas)} fontes com falha"
          f" (tentativa {tentativa}, triagem {'ok' if triagem_ok else 'falhou'})")


if __name__ == "__main__":
    rodar(se_preciso="--se-preciso" in sys.argv)
