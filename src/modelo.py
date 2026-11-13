"""Camada fina sobre o Gemini. Trocar de provedor (ex.: Haiku) = reescrever só este arquivo.

RADAR_FAKE=1 usa respostas simuladas (testes e desenvolvimento sem chave).
"""
import json
import os
import re
import time

FAKE = os.environ.get("RADAR_FAKE") == "1"
MODELO = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")
# a camada gratuita tem cota diária (20 chamadas) separada por modelo: a triagem usa o
# modelo lite para não competir com a redação
MODELO_TRIAGEM = os.environ.get("GEMINI_MODEL_TRIAGEM", "gemini-flash-lite-latest")
# redação também em lite: o Flash completo deu 504 repetido em 2026-10-30 (demanda alta)
MODELO_REDACAO = os.environ.get("GEMINI_MODEL_REDACAO", MODELO_TRIAGEM)
# se o modelo escolhido seguir indisponível (503 de "alta demanda" durou 2 dias seguidos em
# 11-12/11/2026 e derrubou a rodada), tenta estes na ordem; cada modelo tem cota própria
ALTERNATIVOS = [m for m in os.environ.get("GEMINI_ALTERNATIVOS", MODELO).split(",") if m]
TIMEOUT_MS = 180_000  # 3 min por chamada
_PAUSA = 6.5  # a camada gratuita limita requisições por minuto

_cliente = None


def _client():
    global _cliente
    if _cliente is None:
        from google import genai
        from google.genai import types
        # sem teto, uma chamada travada (comum em vídeo) prende a rodada inteira
        _cliente = genai.Client(api_key=os.environ["GEMINI_API_KEY"],
                                http_options=types.HttpOptions(timeout=TIMEOUT_MS))
    return _cliente


class CotaDiaria(Exception):
    """Cota diária do modelo esgotada: insistir não adianta até a renovação."""


def gerar_json(prompt, esquema, video_url=None, modelo=None, tentativas=3, timeout_ms=None):
    """Chamada com saída estruturada. `esquema` é um schema JSON; video_url opcional
    faz o Gemini assistir um vídeo público do YouTube. Esgotadas as tentativas num modelo,
    passa ao próximo de ALTERNATIVOS; só levanta erro se todos falharem."""
    principal = modelo or MODELO
    cadeia = [principal] + [m for m in ALTERNATIVOS if m != principal]
    ultimo = None
    for m in cadeia:
        try:
            return _gerar_com(m, prompt, esquema, video_url, tentativas, timeout_ms)
        except Exception as e:
            ultimo = e
            print(f"  gemini: {m} falhou ({str(e)[:100]}); "
                  f"{'tentando o próximo modelo' if m != cadeia[-1] else 'sem mais modelos'}", flush=True)
    raise ultimo


def _gerar_com(modelo, prompt, esquema, video_url, tentativas, timeout_ms):
    from google.genai import types
    partes = []
    if video_url:
        partes.append(types.Part(file_data=types.FileData(file_uri=video_url)))
    partes.append(types.Part(text=prompt))
    for tentativa in range(tentativas):
        print(f"  gemini: {modelo} {'(vídeo) ' if video_url else ''}tentativa {tentativa + 1}", flush=True)
        try:
            r = _client().models.generate_content(
                model=modelo,
                contents=types.Content(parts=partes),
                config=types.GenerateContentConfig(
                    response_mime_type="application/json", response_schema=esquema,
                    temperature=0.3,
                    http_options=types.HttpOptions(timeout=timeout_ms or TIMEOUT_MS)),
            )
            time.sleep(_PAUSA)
            return json.loads(r.text)
        except Exception as e:
            if "PerDay" in str(e):
                raise CotaDiaria(str(e)[:200]) from e
            if tentativa == tentativas - 1:
                raise
            # 429/503 pedem espera longa; outros erros, tentativa rápida
            espera = 30 * (tentativa + 1) if re.search(r"429|503|quota|rate|demand", str(e), re.I) else 5
            time.sleep(espera)
