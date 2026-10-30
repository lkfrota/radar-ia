"""Triagem em lote: o modelo dá nota de aderência e novidade a cada candidato."""
import hashlib

from . import modelo

LOTE = 25

ESQUEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "i": {"type": "INTEGER"},
            "aderencia": {"type": "NUMBER"},
            "novidade": {"type": "NUMBER"},
            "tema": {"type": "STRING"},
        },
        "required": ["i", "aderencia", "novidade", "tema"],
    },
}


def _prompt(perfil, lote):
    linhas = []
    for n, it in enumerate(lote):
        resumo = (it.texto or "")[:500].replace("\n", " ")
        linhas.append(f"[{n}] ({it.fonte}) {it.titulo} — {resumo}")
    return (
        "Você faz a triagem diária de notícias de IA para um engenheiro mecânico (20 anos em "
        "manutenção industrial) que hoje tem uma empresa de projetos fotovoltaicos e faz "
        "consultoria de IA/dados. Ele não é programador profissional.\n\n"
        "INTERESSES:\n- " + "\n- ".join(perfil["interesses"]) + "\n\n"
        "NÃO-INTERESSES:\n- " + "\n- ".join(perfil["nao_interesses"]) + "\n\n"
        "Para cada candidato dê: aderencia (0-10: quão útil/atual para esse perfil; "
        "nao-interesses derrubam a nota), novidade (0-10: quão provável de ser algo que ele "
        "ainda não conhece, mas que tem correlação com o perfil) e tema (2-4 palavras, "
        "minúsculas, reutilize os mesmos rótulos para assuntos iguais). Itens fora de IA/"
        "tecnologia aplicada recebem aderencia 0.\n\nCANDIDATOS:\n" + "\n".join(linhas)
    )


def _fake(it, perfil):
    """Pontuação simulada determinística, por sobreposição de palavras com o perfil."""
    palavras = {p.lower() for t in perfil["interesses"] for p in t.replace(",", " ").split() if len(p) > 4}
    alvo = set((it.titulo + " " + it.texto[:300]).lower().replace(",", " ").split())
    ader = min(10, 3 + 2 * len(palavras & alvo))
    nov = int(hashlib.md5(it.url.encode()).hexdigest(), 16) % 10
    return {"aderencia": ader, "novidade": nov, "tema": "simulado"}


def pontuar(itens, perfil):
    """Anexa .aderencia, .novidade e .tema a cada Item (atributos dinâmicos)."""
    if modelo.FAKE:
        for it in itens:
            for k, v in _fake(it, perfil).items():
                setattr(it, k, v)
        return itens
    for ini in range(0, len(itens), LOTE):
        lote = itens[ini:ini + LOTE]
        res = modelo.gerar_json(_prompt(perfil, lote), ESQUEMA)
        por_i = {r["i"]: r for r in res}
        for n, it in enumerate(lote):
            r = por_i.get(n, {"aderencia": 0, "novidade": 0, "tema": "indefinido"})
            it.aderencia, it.novidade, it.tema = r["aderencia"], r["novidade"], r["tema"]
    return itens
