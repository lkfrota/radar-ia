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


def test_feedback(tmp_path):
    (tmp_path / "1.json").write_text(json.dumps({"url": "u", "tema": "t", "fonte": "f", "acao": "dislike"}))
    (tmp_path / "2.json").write_text(json.dumps({"url": "v", "tema": "t", "fonte": "f", "acao": "like"}))
    p, pend, vistos = pesos.processar(tmp_path, {"temas": {}, "fontes": {}}, [{"url": "u"}, {"url": "v"}], [])
    assert p["temas"]["t"] == -0.05  # -0.15 + 0.10
    assert [x["url"] for x in pend] == ["v"] and vistos == ["u"]
    assert not list(tmp_path.glob("*.json"))
