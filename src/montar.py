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


ESQUEMA = {
    "type": "OBJECT",
    "properties": {
        "titulo": {"type": "STRING"},
        "paragrafos": {"type": "ARRAY", "items": {"type": "STRING"}},
        "por_que_importa": {"type": "STRING"},
    },
    "required": ["titulo", "paragrafos", "por_que_importa"],
}


def _prompt(it, alvo, perfil):
    base = (
        "Escreva em português do Brasil, tom direto e claro, para um engenheiro mecânico "
        "que não é programador profissional. Explique termos técnicos na primeira vez. "
        f"Resuma o conteúdo abaixo em {alvo}, sem inventar nada além da fonte. Dê também "
        "'por_que_importa': uma frase ligando ao perfil dele (manutenção industrial, "
        "energia solar, agentes de IA, consultoria de dados) ou dizendo honestamente que é "
        "só uma aposta de correlação.\n\n"
        f"Título original: {it.titulo}\nFonte: {it.fonte}\n"
    )
    if it.tipo == "video":
        return base + "O conteúdo é o vídeo anexado."
    return base + f"Conteúdo:\n{it.texto}"


def redigir(it, perfil):
    alvo = paragrafos_alvo(it.nota)
    if modelo.FAKE:
        return {"titulo": it.titulo, "paragrafos": [f"(simulado) Resumo de {it.titulo}."] * (
            4 if it.nota >= 8 else 2 if it.nota >= 5 else 1), "por_que_importa": "(simulado)"}
    # vídeo só é assistido pelo modelo se a nota justificar; senão resume título/descrição
    video = it.url if it.tipo == "video" and it.nota >= 6 else None
    try:
        return modelo.gerar_json(_prompt(it, alvo, perfil), ESQUEMA, video_url=video)
    except Exception:
        if not video:
            raise
        it.tipo = "video-sem-conteudo"  # cota de vídeo estourou: cai para título
        return modelo.gerar_json(_prompt(it, alvo, perfil), ESQUEMA)
