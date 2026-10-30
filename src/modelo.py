"""Camada fina sobre o Gemini. Trocar de provedor (ex.: Haiku) = reescrever só este arquivo.

RADAR_FAKE=1 usa respostas simuladas (testes e desenvolvimento sem chave).
"""
import json
import os
import re
import time

FAKE = os.environ.get("RADAR_FAKE") == "1"
MODELO = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")
_PAUSA = 6.5  # a camada gratuita limita requisições por minuto

_cliente = None


def _client():
    global _cliente
    if _cliente is None:
        from google import genai
        _cliente = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _cliente


def gerar_json(prompt, esquema, video_url=None):
    """Chamada com saída estruturada. `esquema` é um schema JSON; video_url opcional
    faz o Gemini assistir um vídeo público do YouTube."""
    from google.genai import types
    partes = []
    if video_url:
        partes.append(types.Part(file_data=types.FileData(file_uri=video_url)))
    partes.append(types.Part(text=prompt))
    for tentativa in range(3):
        try:
            r = _client().models.generate_content(
                model=MODELO,
                contents=types.Content(parts=partes),
                config=types.GenerateContentConfig(
                    response_mime_type="application/json", response_schema=esquema,
                    temperature=0.3),
            )
            time.sleep(_PAUSA)
            return json.loads(r.text)
        except Exception as e:
            if tentativa == 2:
                raise
            espera = 30 * (tentativa + 1) if re.search(r"429|quota|rate", str(e), re.I) else 5
            time.sleep(espera)
