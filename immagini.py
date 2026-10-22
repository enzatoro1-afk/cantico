# -*- coding: utf-8 -*-
"""
immagini.py
===========
Genera l'IMMAGINE del post con l'AI: quella sfondo che va sotto il
versetto (o che diventa la foto del post).

Due motori, in quest'ordine:
1. **Google Gemini** (quello con cui scrivi l'interpretazione): genera
   l'immagine migliore. Serve la chiave, che gia' usi per l'app.
2. **Pollinations** (gratis, senza chiave): il ripiego, cosi' funziona
   anche per chi non ha ancora la chiave Gemini.

Perche' serve: cosi' il post e' COMPLETO senza programmi esterni:
   canzone + immagine generata + testo scritto = post pronto.
"""

from __future__ import annotations

import base64
import os
import tempfile
import time
from urllib.parse import quote

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

# i modelli Gemini che sanno disegnare (il primo che risponde va bene)
MODELLI_IMMAGINE = (
    "gemini-2.5-flash-image",
    "gemini-2.0-flash-preview-image-generation",
    "gemini-3.5-flash-image",
)

# la dimensione giusta per un post verticale 9:16
LARGHEZZA = 1080
ALTEZZA = 1920

URL_API = "https://generativelanguage.googleapis.com/v1beta/models"
URL_POLLINATIONS = "https://image.pollinations.ai/prompt/"

_STILE = (
    "vertical poster 9:16, cinematic soft light, warm and hopeful mood, "
    "gentle sunrise over hills and open sky, subtle golden glow, "
    "painted digital art, no text, no letters, no words, no watermark, "
    "high detail, beautiful composition"
)


def _salva(estensione: str = ".png") -> str:
    return os.path.join(tempfile.gettempdir(),
                        "cantico_immagine" + str(int(time.time())) + estensione)


def prompt_immagine(versetto: str, tema: str = "", stile: str = "",
                    extra: str = "") -> str:
    """
    Costruisce il prompt per l'immagine: il versetto (il significato, non
    le parole) + il tema + lo stile.
    """
    _p = []
    if versetto:
        _p.append(f"A serene scene that expresses this meaning: {versetto}")
    if tema:
        _p.append(f"theme: {tema}")
    if stile:
        _p.append(f"style: {stile}")
    if extra:
        _p.append(extra)
    _p.append(_STILE)
    return ". ".join(_p)


def _gemini(prompt: str, chiave: str) -> dict:
    """Genera l'immagine con Gemini."""
    if requests is None or not chiave:
        return {"ok": False, "errore": "Gemini non disponibile"}
    for _modello in MODELLI_IMMAGINE:
        _url = f"{URL_API}/{_modello}:generateContent"
        try:
            _r = requests.post(
                _url,
                params={"key": chiave},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "responseModalities": ["TEXT", "IMAGE"],
                    },
                },
                timeout=120,
            )
        except Exception as _e:
            return {"ok": False, "errore": f"Gemini: {str(_e)[:120]}"}
        if _r.status_code != 200:
            continue
        try:
            _d = _r.json() or {}
        except Exception:
            continue
        for _c in (_d.get("candidates") or []):
            for _p in ((_c.get("content") or {}).get("parts") or []):
                _inline = _p.get("inlineData") or _p.get("inline_data")
                if _inline and _inline.get("data"):
                    try:
                        _raw = base64.b64decode(_inline["data"])
                    except Exception:
                        continue
                    _mime = _inline.get("mimeType", "image/png")
                    _est = ".png" if "png" in _mime else ".jpg"
                    _path = _salva(_est)
                    with open(_path, "wb") as _f:
                        _f.write(_raw)
                    return {"ok": True, "file": _path,
                            "fonte": f"Gemini ({_modello})", "errore": None}
    return {"ok": False, "errore": "Gemini non ha generato l'immagine"}


def _pollinations(prompt: str) -> dict:
    """Genera l'immagine con Pollinations (gratis, senza chiave)."""
    if requests is None:
        return {"ok": False, "errore": "requests non installato"}
    _url = (f"{URL_POLLINATIONS}{quote(prompt)}"
            f"?width={LARGHEZZA}&height={ALTEZZA}&nologo=true&seed={int(time.time())}")
    try:
        _r = requests.get(_url, timeout=120, stream=True)
    except Exception as _e:
        return {"ok": False, "errore": f"Pollinations: {str(_e)[:120]}"}
    if _r.status_code != 200:
        return {"ok": False,
                "errore": f"Pollinations ha risposto {_r.status_code}"}
    _est = ".jpg"
    _ct = (_r.headers.get("Content-Type") or "").lower()
    if "png" in _ct:
        _est = ".png"
    _path = _salva(_est)
    with open(_path, "wb") as _f:
        for _chunk in _r.iter_content(8192):
            if _chunk:
                _f.write(_chunk)
    if os.path.getsize(_path) < 2000:
        try:
            os.remove(_path)
        except Exception:
            pass
        return {"ok": False, "errore": "Immagine troppo piccola: riprova"}
    return {"ok": True, "file": _path, "fonte": "Pollinations (gratis)",
            "errore": None}


def genera_immagine(versetto: str = "", tema: str = "", stile: str = "",
                    chiave_gemini: str = "", extra: str = "") -> dict:
    """
    Genera l'immagine del post.

    Restituisce {"ok": bool, "file": str, "fonte": str, "errore": str|None}
    """
    _prompt = prompt_immagine(versetto, tema, stile, extra)
    if (chiave_gemini or "").strip():
        _r = _gemini(_prompt, chiave_gemini.strip())
        if _r.get("ok"):
            return _r
        # Gemini ha fallito: ripiego su Pollinations
        _r2 = _pollinations(_prompt)
        if _r2.get("ok"):
            _r2["nota"] = _r.get("errore")
            return _r2
        return {"ok": False, "file": "", "fonte": "",
                "errore": (f"{_r.get('errore')} / {_r2.get('errore')}")}
    return _pollinations(_prompt)
