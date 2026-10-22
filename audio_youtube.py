# -*- coding: utf-8 -*-
"""
audio_youtube.py
================
Scarica l'AUDIO (mp3) di un video di YouTube, cosi' l'utente puo':
  - ascoltarlo per capire se e' la canzone giusta
  - usarlo per montare il video (in locale)
  - avere il file in mano

NOTA SUL DIRITTI (importante, e' spiegato anche nell'app):
    l'mp3 di una canzone di un artista e' un'opera protetta. Ricaricarlo
    su TikTok NON funziona: TikTok riconosce la musica e ti muta il video
    (o lo toglie), e rischi lo strike. Per pubblicare, il modo giusto e' usare
    il SUONO ORIGINALE dalla libreria audio di TikTok ("Prendi il suono su
    TikTok"), che e' la stessa canzone senza alcun problema.
    Questo download serve per ascoltare e per il video locale.
"""

from __future__ import annotations

import os
import subprocess
import tempfile


def _ytdlp() -> str:
    """Il percorso dell'eseguibile yt-dlp (se installato)."""
    try:
        import shutil
        _p = shutil.which("yt-dlp")
        if _p:
            return _p
    except Exception:
        pass
    try:
        import yt_dlp  # noqa: F401
        return "yt-dlp"
    except Exception:
        return ""


def scarica_audio(url: str, durata_max: int = 600) -> dict:
    """
    Scarica l'audio di un video di YouTube.

    Restituisce {"ok": bool, "file": str, "errore": str|None}
    """
    if not (url or "").strip():
        return {"ok": False, "file": "", "errore": "Link mancante."}
    _exe = _ytdlp()
    if not _exe:
        return {"ok": False, "file": "",
                "errore": "yt-dlp non e' installato su questo server."}
    _out = os.path.join(tempfile.gettempdir(), "cantico_audio")
    _comando = [
        _exe, "-x", "--audio-format", "mp3", "--audio-quality", "0",
        "--no-playlist", "--no-warnings", "--quiet",
        "-o", _out, url,
    ]
    try:
        _r = subprocess.run(_comando, capture_output=True, timeout=300)
    except subprocess.TimeoutExpired:
        return {"ok": False, "file": "", "errore": "Download scaduto."}
    except Exception as _e:
        return {"ok": False, "file": "", "errore": str(_e)[:120]}
    if _r.returncode != 0:
        _err = (_r.stderr or b"").decode("utf-8", "replace").strip()
        return {"ok": False, "file": "",
                "errore": (_err[-160:] if _err else
                           "Non sono riuscito a scaricare l'audio.")}
    # il file finale ha l'estensione mp3
    for _f in sorted(os.listdir(tempfile.gettempdir())):
        if _f.startswith("cantico_audio") and _f.endswith(".mp3"):
            _p = os.path.join(tempfile.gettempdir(), _f)
            if os.path.getsize(_p) > 20000:
                return {"ok": True, "file": _p, "errore": None}
    return {"ok": False, "file": "", "errore": "File audio non trovato."}
