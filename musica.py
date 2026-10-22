# -*- coding: utf-8 -*-
"""
musica.py
=========
Canzone ORIGINALE per il post: testo -> musica cantata -> video TikTok.

Solo motori GRATUITI (nessuna chiave a pagamento):
  1) SUNO     - i crediti gratuiti giornalieri del TUO account, tramite il
                servizio open source "suno-api" (vedi suno.py). Canta le
                parole: e' il motore giusto per un cantico.
  2) ACE-Step - open source su Hugging Face: canta il testo. Gratis, ma
                coda (puo' mettersi in attesa).
  3) MusicGen - open source: solo strumentale (ottimo come base).

  4) VIDEO    - la canzone e' un audio, ma TikTok accetta SOLO .mp4.
                Quindi: immagine di sfondo (1080x1920, verticale) + audio
                -> .mp4 con ffmpeg (incluso in imageio-ffmpeg, cosi' funziona
                anche su Streamlit Cloud senza installare nulla a mano).
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

# i motori gratuiti, in ordine di preferenza
MOTORI_GRATUITI = (
    "ACE-Step (canta il brano - automatico)",
    "Suno (i tuoi crediti gratuiti)",
    "MusicGen (strumentale)",
    "Treblo (canta il testo - serve la carta)",
)


# stile musicale di default: inno pentecostale, voce maschile, piano
STILE_DEFAULT = ("Inno di lode pentecostale, voce maschile, piano e cori "
                 "soft, atmosfera calda e devozionale, 78 BPM")


# --------------------------------------------------------------------------
# 1) La musica
# --------------------------------------------------------------------------

def genera_canzone(lyrics: str, stile: str = "", modello: str = "",
                   timeout: int = 600) -> dict:
    """
    Compone e canta il brano con i motori gratuiti, in ordine:
      1) Suno      - i tuoi crediti gratuiti (se il servizio e' attivo)
      2) ACE-Step  - open source, canta il testo
      3) MusicGen  - open source, solo strumentale

    Se 'modello' e' indicato, si prova SOLO quello.

    Restituisce:
      {"ok": True,  "file": "<percorso mp3>", "url": "...", "motore": "..."}
      {"ok": False, "errore": "..."}
    """
    vuoto = {"ok": False, "errore": "", "file": "", "url": "", "motore": ""}
    lyrics = (lyrics or "").strip()
    if len(lyrics) < 10:
        return {**vuoto, "errore": "Le parole sono troppo corte per un brano."}
    stile = (stile or STILE_DEFAULT).strip()

    scelte = ([modello] if modello else
              ["ace-step", "suno", "musicgen", "treblo"])
    problemi = []
    for scelta in scelte:
        if scelta == "suno":
            try:
                import suno as _suno
                r = _suno.genera_canzone_suno(lyrics, tags=stile,
                                              timeout=min(timeout, 480))
            except Exception as exc:
                r = {"ok": False, "errore": f"Suno: {str(exc)[:120]}"}
        elif scelta == "treblo":
            try:
                import treblo as _treblo
                r = _treblo.genera_canzone_treblo(lyrics, tags=stile,
                                                  timeout=timeout)
            except Exception as exc:
                r = {"ok": False, "errore": f"Treblo: {str(exc)[:120]}"}
        else:
            r = genera_canzone_gratuita(lyrics, stile, modello=scelta,
                                        timeout=timeout)
        if r.get("ok"):
            return r
        problemi.append(f"{scelta}: {r.get('errore', '')[:110]}")
    return {**vuoto, "errore": " | ".join(problemi) or "nessun motore disponibile"}



# --------------------------------------------------------------------------
# MOTORI gratuiti (open source su Hugging Face)
# --------------------------------------------------------------------------
# ACE-Step e' l'alternativa libera a Suno: genera un brano completo, con la
# voce che CANTa le parole. MusicGen fa solo lo strumentale.
# Non serve nessuna chiave: sono Space pubblici (coda e attesa, ma gratis).

SPACE_ACE_STEP = "ACE-Step/ACE-Step"
SPACE_MUSICGEN = "facebook/MusicGen"


def token_huggingface() -> str:
    """
    Il token Hugging Face (gratis) serve per la quota GPU di ACE-Step e
    MusicGen. Senza token gli Space pubblici rispondono "quota esaurita".
    Lo prende dai secrets, dalle variabili d'ambiente o dalla barra
    laterale dell'app.
    """
    for nome in ("HF_TOKEN", "HUGGINGFACE_TOKEN", "HUGGING_FACE_HUB_TOKEN"):
        try:
            import streamlit as st
            v = str(st.secrets.get(nome, "") or "").strip()
            if v:
                return v
        except Exception:
            pass
        v = str(os.environ.get(nome, "") or "").strip()
        if v:
            return v
    try:
        import streamlit as st
        v = str(st.session_state.get("token_hf", "") or "").strip()
        if v:
            return v
    except Exception:
        pass
    # il file locale dei secrets
    try:
        import tomllib
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         ".streamlit", "secrets.toml")
        if os.path.exists(p):
            with open(p, "rb") as f:
                d = tomllib.load(f)
            for nome in ("HF_TOKEN", "HUGGINGFACE_TOKEN",
                         "HUGGING_FACE_HUB_TOKEN"):
                v = str(d.get(nome, "") or "").strip()
                if v:
                    return v
    except Exception:
        pass
    # la chiave condivisa sul server (per tutti)
    try:
        import json
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         ".chiave_hf_server.json")
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                d = json.load(f)
            v = str(d.get("HF_TOKEN", "") or "").strip()
            if v:
                return v
    except Exception:
        pass
    return ""


def ricorda_token_hf(token: str) -> bool:
    """Salva il token sul server, cosi' vale per TUTTI gli utenti dell'app."""
    token = (token or "").strip()
    if not token:
        return False
    try:
        import json
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         ".chiave_hf_server.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump({"HF_TOKEN": token}, f)
        return True
    except Exception:
        return False


def _gradio_client(space: str):
    """Il client Gradio per uno Space pubblico (None se non c'e')."""
    try:
        from gradio_client import Client
    except ImportError:
        return None
    # il token Hugging Face: alcune versioni di gradio_client lo leggono
    # solo dalla variabile d'ambiente
    _tok = token_huggingface()
    if _tok:
        os.environ["HF_TOKEN"] = _tok
        os.environ["HUGGING_FACE_HUB_TOKEN"] = _tok
    try:
        try:
            return Client(space, verbose=False, hf_token=_tok or None)
        except TypeError:
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
        _msg = str(exc)
        if "quota" in _msg.lower() or "ZeroGPU" in _msg:
            return {**vuoto, "errore": (
                "ACE-Step: la quota GPU gratuita di oggi e' finita (si azzera "
                "domani: sono poche canzoni al giorno per account). "
                "Intanto puoi usare Suno (i tuoi crediti) o MusicGen, "
                "oppure riprova domani.")}
        return {**vuoto, "errore": f"ACE-Step non ha risposto: {_msg[:250]}"}

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
        _msg = str(exc)
        if "quota" in _msg.lower() or "ZeroGPU" in _msg:
            return {**vuoto, "errore": (
                "MusicGen: la quota GPU gratuita di oggi e' finita (si azzera "
                "domani). Riprova domani, oppure usa ACE-Step o Suno.")}
        return {**vuoto, "errore": f"MusicGen non ha risposto: {_msg[:250]}"}
    path = _percorso_audio(risultato)
    if not path:
        return {**vuoto, "errore": "MusicGen ha risposto senza un file audio."}
    return {"ok": True, "errore": "", "file": path,
            "motore": "MusicGen (open source, gratis, strumentale)"}


def _percorso_audio(risultato) -> str:
    """Dalla risposta di Gradio estrae il percorso del file audio."""
    try:
        # ACE-Step risponde con una tupla: [percorso_file, parametri]
        if isinstance(risultato, (list, tuple)) and risultato:
            _primo = risultato[0]
            if isinstance(_primo, str) and os.path.exists(_primo):
                return _primo
            risultato = _primo
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
        if isinstance(risultato, str) and os.path.exists(risultato):
            return risultato
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
      1) Suno      (i crediti gratuiti del tuo account)
      2) ACE-Step  (canta il testo)
      3) MusicGen  (solo strumentale)
    """
    return genera_canzone(lyrics, stile, timeout=timeout)



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


