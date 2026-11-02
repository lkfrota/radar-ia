import json
from src.coletar import Item
from src import montar, pesos


def item(url, ader, nov, tema="agentes", fonte="F", desc=False):
    i = Item(url, "t", fonte, "artigo", descoberta=desc)
    i.aderencia, i.novidade, i.tema = ader, nov, tema
    return i


def test_cotas_e_vistos():
    itens = [item(f"u{n}", 9, 5) for n in range(10)] + [item(f"a{n}", 5, 6) for n in range(5)]
    itens.append(item("x", 3.5, 9, desc=True))  # abaixo do limiar adjacente, sem categoria
    itens.append(item("visto", 9, 9))
    sel = montar.selecionar(itens, {"temas": {}, "fontes": {}}, {"visto"})
    assert len(sel) == montar.TOTAL
    assert "visto" not in [i.url for i in sel]
    assert sum(i.categoria == "adjacente" for i in sel) >= 3


def test_exploratorio_so_descoberta():
    assert montar.categoria(item("a", 3, 9, desc=True)) == "exploratorio"
    assert montar.categoria(item("a", 3, 9, desc=False)) is None


def test_peso_dislike_reduz_nota():
    p = {"temas": {"agentes": -0.5}, "fontes": {}}
    assert montar.nota(item("a", 8, 8), p) < montar.nota(item("a", 8, 8), {"temas": {}, "fontes": {}})


def test_profundidade():
    assert montar.paragrafos_alvo(9) == "4 a 5 parágrafos"
    assert montar.paragrafos_alvo(6) == "2 a 3 parágrafos"
    assert montar.paragrafos_alvo(2) == "1 parágrafo"


def _fb(tmp_path, nome, url, acao):
    (tmp_path / nome).write_text(json.dumps({"url": url, "tema": "t", "fonte": "f", "acao": acao}))


def test_fonte_recebe_so_fracao_do_sinal(tmp_path):
    _fb(tmp_path, "1.json", "a", "fora_foco")
    _fb(tmp_path, "2.json", "b", "quero_mais")
    _fb(tmp_path, "3.json", "c", "util")
    p, pend, vistos = pesos.processar(tmp_path, {"temas": {}, "fontes": {}},
                                      [{"url": u} for u in "abcd"], [])
    assert p["temas"]["t"] == 0.08   # -0.15 + 0.15 + 0.08
    assert p["fontes"]["f"] == 0.03  # -0.05 + 0.05 + 0.03
    assert [x["url"] for x in pend] == ["d"] and sorted(vistos) == ["a", "b", "c"]
    assert not list(tmp_path.glob("*.json"))


def test_ja_conhecia_reduz_novidade(tmp_path):
    _fb(tmp_path, "1.json", "a", "ja_conhecia")
    p, _, _ = pesos.processar(tmp_path, {"temas": {}, "fontes": {}}, [], [])
    assert p["temas"] == {} and p["conhecido"] == {"t": 1}
    assert montar.nota(item("x", 8, 10, tema="t"), p) < montar.nota(item("x", 8, 10, tema="t"), {"temas": {}, "fontes": {}})


def test_feedback_legado(tmp_path):
    _fb(tmp_path, "1.json", "a", "like")
    p, _, vistos = pesos.processar(tmp_path, {"temas": {}, "fontes": {}}, [], [])
    assert p["temas"]["t"] == 0.08 and vistos == ["a"]


def test_falha_do_modelo_nao_derruba_rodada(monkeypatch):
    from src import modelo
    def quebra(*a, **k):
        raise RuntimeError("504 DEADLINE_EXCEEDED")
    monkeypatch.setattr(modelo, "FAKE", False)
    monkeypatch.setattr(modelo, "gerar_json", quebra)
    v = item("v", 9, 5); v.tipo = "video"; v.nota = 9
    a = item("a", 9, 5); a.texto = "corpo original do artigo"; a.nota = 7
    out = montar.redigir_lote([v, a])
    assert set(out) == {"v", "a"}
    assert "corpo original" in out["a"]["paragrafos"][0]


def test_fonte_arquivo_avisa_quando_velha(tmp_path, monkeypatch):
    from src import coletar
    from datetime import datetime, timedelta, timezone
    (tmp_path / "e.json").write_text(json.dumps({
        "atualizado": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat(),
        "itens": [{"url": "u", "titulo": "t", "texto": "x"}]}))
    monkeypatch.setattr(coletar, "RAIZ", tmp_path)
    coletar.AVISOS.clear()
    itens, falhas = coletar.coletar_tudo([{"nome": "TB", "tipo": "arquivo", "arquivo": "e.json"}])
    assert [i.url for i in itens] == ["u"] and "5 dias" in falhas[0]["erro"]
