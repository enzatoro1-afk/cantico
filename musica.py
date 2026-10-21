# -*- coding: utf-8 -*-
"""
musica.py
=========
Canzone ORIGINALE per il post: testo -> musica cantata -> video TikTok.

Due tappe:
  1) MUSICA  - AIMLAPI (motori di generazione audio con voce).
     POST https://api.aimlapi.com/v2/generate/audio  ->  {"generation_id": ...}
     poi si interroga lo stesso endpoint finche' il brano e' pronto:
     {"status": "success", "output": [{"url": "....mp3"}]}

  2) VIDEO  - la canzone e' un audio, ma TikTok accetta SOLO .mp4.
     Quindi: immagine di sfondo (1080x1920, verticale) + audio -> .mp4
     con ffmpeg ( incluso in imageio-ffmpeg, cosi' funziona anche su
     Streamlit Cloud senza installare nulla a mano).

NOTA SUI MODELLI (verificato sui docs AIMLAPI):
  - "suno" NON e' disponibile come modello chiamabile
  - i modelli che cantano davvero le parole sono:
      minimax/music-2.6   (lyrics separate + voce, il migliore per un inno)
      minimax/music-2.0, minimax/music-1.5
      elevenlabs/eleven_music (lyrics dentro il prompt)
      google/lyria-2 (lyrics nel prompt, max 600 caratteri)
  - il FREE TIER di AIMLAPI al momento e' in PAUSA: serve una chiave
    con credito. L'app lo dice chiaramente se la chiamata fallisce.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import time
import uuid
from urllib.parse import urlparse

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore

URL_AIMLAPI = "https://api.aimlapi.com/v2/generate/audio"

# i modelli che cantano le parole, dal piu' adatto al piu' semplice
MODELLI_CANTATI = (
    "minimax/music-2.6",
    "minimax/music-2.0",
    "elevenlabs/eleven_music",
    "google/lyria-2",
)

# stile musicale di default: inno pentecostale, voce maschile, piano
STILE_DEFAULT = ("Inno di lode pentecostale, voce maschile, piano e cori "
                 "soft, atmosfera calda e devozionale, 78 BPM")


# --------------------------------------------------------------------------
# 1) La musica
# --------------------------------------------------------------------------

def genera_canzone(lyrics: str, stile: str = "", chiave: str = "",
                   modello: str = "", timeout: int = 420) -> dict:
    """
    Chiede ad AIMLAPI di comporre e cantare il brano.

    Restituisce:
      {"ok": True,  "file": "<percorso mp3>", "url": "...", "modello": "..."}
      {"ok": False, "errore": "..."}
    """
    vuoto = {"ok": False, "errore": "", "file": "", "url": "", "modello": ""}
    if requests is None:
        return {**vuoto, "errore": "requests non installato"}
    chiave = (chiave or _chiave_da_secrets()).strip()
    if not chiave:
        return {**vuoto, "errore": (
            "Chiave AIMLAPI mancante: mettila nella barra laterale "
            "(campo 'Chiave AIMLAPI'). E' gratis su aimlapi.com "
            "(l'API per generare musica con voce).")}

    lyrics = (lyrics or "").strip()
    if len(lyrics) < 10:
        return {**vuoto, "errore": "Le parole sono troppo corte per un brano."}
    stile = (stile or STILE_DEFAULT).strip()
    modello = modello or MODELLI_CANTATI[0]

    # MiniMax accetta "lyrics" a parte; gli altri modelli vogliono tutto
    # dentro "prompt". Gestiamo i due casi.
    def _corpo(m: str) -> dict:
        if m.startswith("minimax/"):
            return {"model": m, "prompt": stile, "lyrics": lyrics[:3000],
                    "is_instrumental": False}
        return {"model": m, "prompt": f"{stile}\n\n{lyrics}"[:2000]}

    headers = {"Authorization": f"Bearer {chiave}",
               "Content-Type": "application/json"}
    ultimo = ""
    for m in (modello,):
        try:
            risp = requests.post(URL_AIMLAPI, json=_corpo(m), headers=headers,
                                 timeout=60)
        except Exception as exc:
            return {**vuoto, "errore": f"Impossibile contattare AIMLAPI: {exc}"}

        if risp.status_code == 401:
            return {**vuoto, "errore": "Chiave AIMLAPI non valida."}
        if risp.status_code == 402:
            return {**vuoto, "errore": (
                "AIMLAPI: credito esaurito o free tier non attivo al "
                "momento. Serve un piano con crediti (si parte da pochi "
                "euro) oppure attendere che il free tier torni.")}
        if risp.status_code != 200:
            ultimo = f"AIMLAPI errore {risp.status_code}: {risp.text[:200]}"
            continue

        try:
            dati = risp.json()
        except Exception:
            ultimo = "risposta AIMLAPI non leggibile"
            continue

        _gid = (dati.get("generation_id") or dati.get("id")
                or (dati.get("output") or [{}])[0].get("generation_id"))
        if not _gid:
            ultimo = "AIMLAPI non ha restituito un generation_id"
            continue

        # --- attesa del brano ---
        scaduto = time.time() + timeout
        url_audio = ""
        while time.time() < scaduto:
            time.sleep(6)
            try:
                r2 = requests.get(URL_AIMLAPI,
                                  params={"generation_id": _gid},
                                  headers=headers, timeout=45)
                d2 = r2.json()
            except Exception:
                continue
            _st = (d2.get("status") or d2.get("state") or "").lower()
            _out = d2.get("output") or []
            for _o in _out:
                if isinstance(_o, dict) and _o.get("url"):
                    url_audio = _o["url"]
                    break
            if url_audio:
                break
            if _st in ("error", "failed", "canceled"):
                ultimo = (d2.get("error") or d2.get("message")
                          or "generazione fallita")
                break
        if not url_audio:
            return {**vuoto, "errore": ultimo or (
                "Tempo scaduto: il brano non e' pronto. Riprova.")}

        # --- download del file ---
        try:
            file_mp3 = os.path.join(tempfile.gettempdir(),
                                    f"cantico_{uuid.uuid4().hex[:10]}.mp3")
            with requests.get(url_audio, stream=True, timeout=180) as rf:
                with open(file_mp3, "wb") as f:
                    for pezzo in rf.iter_content(65536):
                        if pezzo:
                            f.write(pezzo)
        except Exception as exc:
            return {**vuoto, "errore": f"Brano pronto ma download fallito: {exc}"}

        return {"ok": True, "errore": "", "file": file_mp3, "url": url_audio,
                "modello": m}

    return {**vuoto, "errore": ultimo or "AIMLAPI non ha risposto"}


# --------------------------------------------------------------------------
# MOTORI gratuiti (open source su Hugging Face)
# --------------------------------------------------------------------------
# ACE-Step e' l'alternativa libera a Suno: genera un brano completo, con la
# voce che CANTa le parole. MusicGen fa solo lo strumentale.
# Non serve nessuna chiave: sono Space pubblici (coda e attesa, ma gratis).

SPACE_ACE_STEP = "ACE-Step/ACE-Step"
SPACE_MUSICGEN = "facebook/MusicGen"


def _gradio_client(space: str):
    """Il client Gradio per uno Space pubblico (None se non c'e')."""
    try:
        from gradio_client import Client
    except ImportError:
        return None
    try:
        return Client(space, verbose=False)
    except Exception:
        return None


def genera_canzone_gratuita(lyrics: str, stile: str = "",
                            durata: int = 60, modello: str = "ace-step",
                            timeout: int = 600) -> dict:
    """
    Compone la canzone GRATIS con un modello open source.

    modello: "ace-step" (canta il testo) | "musicgen" (solo strumentale)

    Restituisce {"ok": True, "file": "<path>", "motore": "..."} oppure
    {"ok": False, "errore": "..."}
    """
    vuoto = {"ok": False, "errore": "", "file": "", "motore": modello}
    lyrics = (lyrics or "").strip()
    stile = (stile or STILE_DEFAULT).strip()

    if modello == "musicgen":
        return _genera_musicgen(stile, durata, timeout)

    if len(lyrics) < 10:
        return {**vuoto, "errore": "Le parole sono troppo corte per un brano."}

    client = _gradio_client(SPACE_ACE_STEP)
    if client is None:
        return {**vuoto, "errore": (
            "gradio_client non e' installato (pip install gradio_client) "
            "oppure lo Space non e' raggiungibile. Riprova fra poco.")}

    try:
        risultato = client.predict(
            audio_duration=durata,
            prompt=stile,
            lyrics=lyrics[:2900],
            infer_step=30,
            guidance_scale=15.0,
            scheduler_type="euler",
            cfg_type="apg",
            omega_scale=10.0,
            manual_seeds="42",
            guidance_interval=0.5,
            guidance_interval_decay=0.0,
            min_guidance_scale=3.0,
            use_erg_tag=True,
            use_erg_lyric=False,
            use_erg_diffusion=True,
            oss_steps="",
            guidance_scale_text=0.0,
            guidance_scale_lyric=0.0,
            audio2audio_enable=False,
            ref_audio_strength=0.5,
            ref_audio_input=None,
            lora_name_or_path="none",
            api_name="/__call__",
        )
    except Exception as exc:
        return {**vuoto, "errore": f"ACE-Step non ha risposto: {str(exc)[:250]}"}

    path = _percorso_audio(risultato)
    if not path:
        return {**vuoto, "errore": "ACE-Step ha risposto senza un file audio."}
    return {"ok": True, "errore": "", "file": path,
            "motore": "ACE-Step (open source, gratis)"}


def _genera_musicgen(stile: str, durata: int, timeout: int) -> dict:
    """MusicGen: solo strumentale (per un sottofondo)."""
    vuoto = {"ok": False, "errore": "", "file": "", "motore": "MusicGen"}
    client = _gradio_client(SPACE_MUSICGEN)
    if client is None:
        return {**vuoto, "errore": "MusicGen non raggiungibile. Riprova fra poco."}
    try:
        risultato = client.predict(
            texts=stile,
            melodies=None,
            api_name="/predict_batched",
        )
    except Exception as exc:
        return {**vuoto, "errore": f"MusicGen non ha risposto: {str(exc)[:250]}"}
    path = _percorso_audio(risultato)
    if not path:
        return {**vuoto, "errore": "MusicGen ha risposto senza un file audio."}
    return {"ok": True, "errore": "", "file": path,
            "motore": "MusicGen (open source, gratis, strumentale)"}


def _percorso_audio(risultato) -> str:
    """Dalla risposta di Gradio estrae il percorso del file audio."""
    try:
        if isinstance(risultato, (list, tuple)) and risultato:
            risultato = risultato[0]
        if isinstance(risultato, dict):
            p = risultato.get("path") or risultato.get("name")
            if p and os.path.exists(p):
                return p
            url = risultato.get("url")
            if url:
                import requests
                out = os.path.join(tempfile.gettempdir(),
                                   f"hf_{uuid.uuid4().hex[:10]}.wav")
                with requests.get(url, stream=True, timeout=180) as r:
                    with open(out, "wb") as f:
                        for pezzo in r.iter_content(65536):
                            if pezzo:
                                f.write(pezzo)
                return out
        p = getattr(risultato, "path", None)
        if p and os.path.exists(p):
            return p
    except Exception:
        pass
    return ""


def genera_canzone_senza_pagare(lyrics: str, stile: str = "",
                                durata: int = 60, timeout: int = 600) -> dict:
    """
    Tenta i motori gratuiti, in ordine:
      1) ACE-Step (canta il testo) - lo spazio piu' adatto a un inno
      2) MusicGen (solo strumentale)
    Se falliscono tutti, prova AIMLAPI (se c'e' credito).
    """
    problemi = []
    for modello in ("ace-step", "musicgen"):
        r = genera_canzone_gratuita(lyrics, stile, durata, modello, timeout)
        if r.get("ok"):
            return r
        problemi.append(f"{modello}: {r.get('errore', '')[:90]}")
    # ultima spiaggia: AIMLAPI (se ha credito)
    r = genera_canzone(lyrics, stile, timeout=min(timeout, 420))
    if r.get("ok"):
        return r
    problemi.append(f"aimlapi: {r.get('errore', '')[:90]}")
    return {"ok": False, "errore": " | ".join(problemi), "file": "",
            "motore": ""}


# --------------------------------------------------------------------------
# 2) Il video per TikTok
# --------------------------------------------------------------------------

def _ffmpeg() -> str:
    """Il binario ffmpeg (da imageio-ffmpeg, cosi' funziona ovunque)."""
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    for cand in ("ffmpeg", "/usr/bin/ffmpeg", "/opt/homebrew/bin/ffmpeg"):
        try:
            subprocess.run([cand, "-version"], capture_output=True, timeout=20)
            return cand
        except Exception:
            continue
    return ""


LARGHEZZA = 1080
ALTEZZA = 1920


def crea_sfondo_verticale(titolo: str, sottotitolo: str = "",
                          colore: tuple[int, int, int] = (30, 20, 60)) -> str:
    """
    Crea un'immagine verticale 1080x1920 (formato TikTok 9:16) con
    sfondo a gradiente e il testo del versetto centrato.
    """
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (LARGHEZZA, ALTEZZA), colore)
    disegna = ImageDraw.Draw(img)

    # gradiente verticale
    for y in range(ALTEZZA):
        t = y / ALTEZZA
        r = int(colore[0] + (88 - colore[0]) * t)
        g = int(colore[1] + (28 - colore[1]) * t)
        b = int(colore[2] + (135 - colore[2]) * t)
        disegna.line([(0, y), (LARGHEZZA, y)], fill=(r, g, b))

    # una stella/luce in alto, per dare "corpo" al video
    for i in range(3):
        cx = 200 + i * 300
        cy = 300 + (i % 2) * 160
        for raggio in range(70, 0, -2):
            a = max(0, 60 - raggio // 3)
            disegna.ellipse([cx - raggio, cy - raggio, cx + raggio, cy + raggio],
                             outline=(255, 255, 255, a) if a else (255, 255, 255))

    _scrivi_testo_centrato(disegna, titolo, 380, 34, (255, 255, 255), True)
    if sottotitolo:
        _scrivi_testo_centrato(disegna, sottotitolo, 1420, 40,
                               (235, 225, 255), False)

    percorso = os.path.join(tempfile.gettempdir(),
                            f"sfondo_{uuid.uuid4().hex[:10]}.png")
    img.save(percorso, "PNG")
    return percorso


def _scrivi_testo_centrato(disegna, testo: str, y: int, dimensione: int,
                           colore, ombra: bool) -> None:
    """Scrive il testo a capo, centrato, con parola per parola."""
    from PIL import ImageFont
    font = _carica_font(dimensione)
    parole = (testo or "").split()
    righe: list[str] = []
    riga = ""
    for p in parole:
        prova = (riga + " " + p).strip()
        try:
            larghezza = disegna.textlength(prova, font=font)
        except Exception:
            larghezza = len(prova) * dimensione * 0.5
        if larghezza > LARGHEZZA - 120 and riga:
            righe.append(riga)
            riga = p
        else:
            riga = prova
    if riga:
        righe.append(riga)

    y0 = y
    for i, r in enumerate(righe):
        try:
            larghezza = disegna.textlength(r, font=font)
        except Exception:
            larghezza = len(r) * dimensione * 0.5
        x = (LARGHEZZA - larghezza) / 2
        yy = y0 + i * int(dimensione * 1.35)
        if ombra:
            disegna.text((x + 3, yy + 3), r, font=font, fill=(0, 0, 0))
        disegna.text((x, yy), r, font=font, fill=colore)


def _carica_font(dimensione: int):
    """Un font qualsiasi (prova DejaVu, poi quello di default)."""
    from PIL import ImageFont
    candidati = [
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\segoeuib.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    ]
    for c in candidati:
        try:
            if os.path.exists(c):
                return ImageFont.truetype(c, dimensione)
        except Exception:
            continue
    try:
        import imageio_ffmpeg  # noqa: F401
    except Exception:
        pass
    return ImageFont.load_default(size=dimensione)


def crea_video_tiktok(audio: str, testo: str = "", sfondo: str = "immagine",
                      immagine_propria: str = "", durata_max: int = 90,
                      muovo: bool = True) -> dict:
    """
    Unisce la canzone a uno sfondo e produce un .mp4 verticale (9:16).

    sfondo: "immagine" (gradiente con il testo) | "nero" | "foto" (tua)
    muovo:  True = leggero zoom (loop animato), False = immagine fissa
    """
    vuoto = {"ok": False, "errore": "", "file": ""}
    if not audio or not os.path.exists(audio):
        return {**vuoto, "errore": "File audio non trovato."}
    exe = _ffmpeg()
    if not exe:
        return {**vuoto, "errore": (
            "ffmpeg non disponibile su questo server. Su Streamlit Cloud "
            "c'e': si aggiorni la app e riprova. Sul PC: pip install "
            "imageio-ffmpeg")}

    # ---------- 1) l'immagine di sfondo ----------
    if sfondo == "foto" and immagine_propria and os.path.exists(immagine_propria):
        img = immagine_propria
    elif sfondo == "nero":
        img = os.path.join(tempfile.gettempdir(), f"nero_{uuid.uuid4().hex[:8]}.png")
        from PIL import Image
        Image.new("RGB", (LARGHEZZA, ALTEZZA), (0, 0, 0)).save(img, "PNG")
    else:
        img = crea_sfondo_verticale(testo or "CANTICO",
                                    "Dalla Parola alla Lode")

    # ---------- 2) il montaggio ----------
    out = os.path.join(tempfile.gettempdir(), f"cantico_{uuid.uuid4().hex[:10]}.mp4")
    vf = "zoompan=z='min(zoom+0.0008,1.25)':d=%d:s=%dx%d:fps=30" % (
        durata_max * 30, LARGHEZZA, ALTEZZA) if muovo else \
        "scale=%d:%d,setsar=1" % (LARGHEZZA, ALTEZZA)

    cmd = [
        exe, "-y",
        "-loop", "1", "-i", img,
        "-i", audio,
        "-vf", vf,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-r", "30",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart",
        out,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              encoding="utf-8", errors="replace",
                              timeout=durata_max * 2 + 120)
    except Exception as exc:
        return {**vuoto, "errore": f"ffmpeg fallito: {exc}"}
    if proc.returncode != 0 or not os.path.exists(out):
        dettaglio = (proc.stderr or "")[-400:]
        return {**vuoto, "errore": f"ffmpeg non ha prodotto il video: {dettaglio}"}

    return {"ok": True, "errore": "", "file": out,
            "durata": _durata_video(out)}


def _durata_video(path: str) -> str:
    try:
        from PIL import Image  # no-op, keeps import simple
    except Exception:
        pass
    try:
        with open(path, "rb") as f:
            dati = f.read()
        return f"{len(dati)/1024/1024:.1f} MB"
    except Exception:
        return ""


def _chiave_da_secrets() -> str:
    """La chiave AIMLAPI dai secrets di Streamlit o dal file locale."""
    for nome in ("AIMLAPI_KEY", "AIML_API_KEY"):
        try:
            import streamlit as st
            v = (st.secrets.get(nome, "") or "").strip()
            if v:
                return v
        except Exception:
            pass
        v = (os.environ.get(nome, "") or "").strip()
        if v:
            return v
    try:
        import tomllib
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         ".streamlit", "secrets.toml")
        if os.path.exists(p):
            with open(p, "rb") as f:
                d = tomllib.load(f)
            for nome in ("AIMLAPI_KEY", "AIML_API_KEY"):
                v = str(d.get(nome, "") or "").strip()
                if v:
                    return v
    except Exception:
        pass
    return ""
