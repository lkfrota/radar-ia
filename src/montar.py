"""Seleção por cotas e redação dos itens do dia."""
from . import modelo

TOTAL = 12
COTAS = {"perfil": 8, "adjacente": 3, "exploratorio": 1}  # soma = TOTAL
LIM_PERFIL = 7.0
LIM_ADJACENTE = 4.0


def nota(it, pesos):
    """Nota final: mistura aderência/novidade e aplica o aprendizado do feedback
    (peso do tema e da fonte, cada um entre -0.5 e +0.5)."""
    base = 0.7 * it.aderencia + 0.3 * it.novidade
    fator = (1 + pesos["temas"].get(it.tema, 0)) * (1 + pesos["fontes"].get(it.fonte, 0))
    return round(min(10, base * fator), 2)


def categoria(it):
    if it.aderencia >= LIM_PERFIL:
        return "perfil"
    if it.aderencia >= LIM_ADJACENTE:
        return "adjacente"
    if it.descoberta and it.novidade >= 8 and it.aderencia >= 3:
        return "exploratorio"
    return None


def selecionar(itens, pesos, vistos):
    """Aplica as cotas; vaga não preenchida numa categoria é repassada às demais por nota."""
    candidatos = []
    for it in itens:
        if it.url in vistos:
            continue
        it.categoria = categoria(it)
        if it.categoria:
            it.nota = nota(it, pesos)
            candidatos.append(it)
    candidatos.sort(key=lambda i: i.nota, reverse=True)
    escolhidos = []
    for cat, cota in COTAS.items():
        escolhidos += [i for i in candidatos if i.categoria == cat][:cota]
    sobra = [i for i in candidatos if i not in escolhidos]
    escolhidos += sobra[:TOTAL - len(escolhidos)]
    return sorted(escolhidos, key=lambda i: i.nota, reverse=True)


def paragrafos_alvo(nota_):
    if nota_ >= 8:
        return "4 a 5 parágrafos"
    if nota_ >= 5:
        return "2 a 3 parágrafos"
    return "1 parágrafo"


MAX_VIDEOS = 1       # vídeo é lento e caro em cota: só os de maior nota são "assistidos"
LOTE_REDACAO = 6     # itens por chamada: lotes menores falham menos
CORPO_LOTE = 2500    # caracteres de texto por item na chamada em lote

ESQUEMA = {
    "type": "OBJECT",
    "properties": {
        "titulo": {"type": "STRING"},
        "paragrafos": {"type": "ARRAY", "items": {"type": "STRING"}},
        "por_que_importa": {"type": "STRING"},
    },
    "required": ["titulo", "paragrafos", "por_que_importa"],
}
ESQUEMA_LOTE = {"type": "ARRAY", "items": {
    "type": "OBJECT",
    "properties": {"i": {"type": "INTEGER"}, **ESQUEMA["properties"]},
    "required": ["i", *ESQUEMA["required"]],
}}

INSTRUCAO = (
    "Escreva em português do Brasil, tom direto e claro, para um engenheiro mecânico "
    "que não é programador profissional. Explique termos técnicos na primeira vez. "
    "Resuma sem inventar nada além da fonte. Dê também 'por_que_importa': uma frase "
    "ligando ao perfil dele (manutenção industrial, energia solar, agentes de IA, "
    "consultoria de dados) ou dizendo honestamente que é só uma aposta de correlação.\n\n"
)


def _fake(it):
    n = 4 if it.nota >= 8 else 2 if it.nota >= 5 else 1
    return {"titulo": it.titulo, "paragrafos": [f"(simulado) Resumo de {it.titulo}."] * n,
            "por_que_importa": "(simulado)"}


def _redigir_video(it):
    p = (INSTRUCAO + f"Resuma o vídeo anexado em {paragrafos_alvo(it.nota)}.\n"
         f"Título original: {it.titulo}\nCanal: {it.fonte}")
    # 1 tentativa e teto curto: vídeo é a chamada mais lenta e instável
    return modelo.gerar_json(p, ESQUEMA, video_url=it.url, modelo=modelo.MODELO_REDACAO,
                             tentativas=1, timeout_ms=120_000)


def _redigir_em_lote(itens):
    blocos = []
    for n, it in enumerate(itens):
        corpo = it.texto[:CORPO_LOTE] if it.texto else (
            "(só título e fonte disponíveis: diga em 1 parágrafo curto que o conteúdo "
            "não foi lido e não invente detalhes)")
        blocos.append(f"[{n}] Título: {it.titulo}\nFonte: {it.fonte}\n"
                      f"Tamanho: {paragrafos_alvo(it.nota)}\nConteúdo: {corpo}")
    res = modelo.gerar_json(INSTRUCAO + "Resuma cada item abaixo no tamanho indicado.\n\n"
                            + "\n\n".join(blocos), ESQUEMA_LOTE, modelo=modelo.MODELO_REDACAO)
    return {r["i"]: r for r in res}


def redigir_lote(itens):
    """Devolve {url: texto}. Gasta ~1 chamada em lote + até MAX_VIDEOS chamadas de vídeo,
    para caber na cota diária gratuita. Cota esgotada: devolve o que já conseguiu."""
    if modelo.FAKE:
        return {it.url: _fake(it) for it in itens}
    out = {}
    video_ok = True  # disjuntor: na primeira falha de vídeo, não tenta os demais
    videos = sorted((i for i in itens if i.tipo == "video" and i.nota >= 6),
                    key=lambda i: i.nota, reverse=True)[:MAX_VIDEOS]
    try:
        for it in videos:
            if not video_ok:
                break
            try:
                out[it.url] = _redigir_video(it)
            except modelo.CotaDiaria:
                raise
            except Exception as e:  # vídeo indisponível/travado: cai para o lote, só com título
                video_ok = False
                print(f"vídeo não lido ({it.url}): {str(e)[:120]}", flush=True)
        resto = [i for i in itens if i.url not in out]
        for ini in range(0, len(resto), LOTE_REDACAO):
            grupo = resto[ini:ini + LOTE_REDACAO]
            res = _redigir_em_lote(grupo)
            for n, it in enumerate(grupo):
                if n in res:
                    out[it.url] = {k: res[n][k] for k in ESQUEMA["required"]}
    except modelo.CotaDiaria as e:
        print(f"cota diária esgotada: {e}", flush=True)
    except Exception as e:  # falha do provedor nunca pode derrubar a rodada
        print(f"redação em lote falhou: {str(e)[:200]}", flush=True)
    for it in itens:
        if it.url not in out:
            out[it.url] = _reserva(it)
    return out


def _reserva(it):
    """Sem IA: título e trecho original, marcado como tal. Melhor que página vazia."""
    trecho = (it.texto or "").strip()[:500]
    return {"titulo": it.titulo,
            "paragrafos": [trecho + "…" if trecho else "Resumo automático indisponível nesta rodada."],
            "por_que_importa": "Resumo automático indisponível nesta rodada; trecho original da fonte."}
