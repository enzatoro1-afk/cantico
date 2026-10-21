# -*- coding: utf-8 -*-
"""
suno.py
=======
Generazione del cantico con SUNO, usando i crediti gratuiti giornalieri del
tuo account (tramite il progetto open source "suno-api", che gira sulla tua
macchina / sul Codespace e parla con suno.com per conto tuo).

Perche' serve un servizio "in locale":
    suno.com non ha un'API pubblica per gli account gratuiti: il progetto
    open source fa da ponte (riceve la richiesta, usa la tua sessione, e
    restituisce l'audio). Per questo l'app parla con
    http://localhost:8000 (di default) invece che con suno.com diretto.

COME USARE (una volta sola):
    1) lancia il servizio open source nella cartella del progetto:
           git clone https://github.com/gcui-art/suno-api
           cd suno-api && npm install && npm start
    2) metti il tuo cookie di suno.com nel file .suno_cookie.txt
       (Nella chat non passarlo: scrivilo direttamente nel file)
    3) nell'app: "Suno (i tuoi crediti gratuiti)" -> "Componi e canta"

Se il servizio non c'e', l'app passa in automatico agli altri motori.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import time
import uuid

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore


# --------------------------------------------------------------------------
# I TAG FISSI: il sound che vogliamo per un cantico evangelico
# --------------------------------------------------------------------------

STILE_CHIESA = ("Modern Christian Worship, contemporary gospel, inspiring, "
                "uplifting, powerful vocal harmony, emotional, "
                "Christian Worship, Gospel, Italian vocal")

STRUMENTI = ("Acoustic guitar, ambient piano, cinematic synths, "
              "build-up drums, emotional strings")

# gli altri tag che aggiungiamo: lingua italiana, voce, qualita'
TAG_AGGIUNTI = "Italian vocals, female and male vocal harmony, worship, "
TAG_AGGIUNTI += "prayer, devotional, studio quality, no spoken intro"

TUTTI_I_TAG = (f"{STILE_CHIESA}, {STRUMENTI}, {TAG_AGGIUNTI}")


# --------------------------------------------------------------------------
# La struttura: il testo diventa [Verse] + [Chorus]
# --------------------------------------------------------------------------

def _ripulisci_lyrics(testo: str) -> str:
    """Toglie prefissi, codici, commenti. Lascia solo le righe del brano."""
    t = (testo or "").strip()
    if not t:
        return ""
    if "```" in t:
        parti = t.split("```")
        t = (parti[1] if len(parti) > 1 else t)
    righe = []
    for r in t.split("\n"):
        r = r.strip()
        if not r:
            continue
        if r.startswith("["):
            righe.append(r)
            continue
        # scarta le frasi di spiegazione
        if re.match(r"^(ecco|certo|sure|ok|bene|incluso|ecco il|testo|canzone|"
                    r"here|verse|chorus)", r, re.IGNORECASE) and len(r) < 70:
            continue
        righe.append(r)
    return "\n".join(righe)


def struttura_canzone(testo: str) -> str:
    """
    Trasforma il testo in un brano con struttura.

    - se il testo ha gia' [Verse]/[Chorus] -> lo tiene (e lo pulisce)
    - altrimenti lo divide: meta' -> [Verse 1], il resto -> [Chorus]
      (un testo lungo viene diviso in piu' strofe + un ritornello finale)
    """
    pulito = _ripulisci_lyrics(testo)
    if not pulito:
        return ""
    if "[Verse" in pulito or "[Chorus" in pulito:
        return pulito

    # divide il testo in frasi (ogni riga = un verso)
    versi = [r for r in pulito.split("\n") if r.strip()]
    if len(versi) < 2:
        return "[Verse]\n" + pulito

    meta = max(1, len(versi) // 2)
    strofe = versi[:meta]
    resto = versi[meta:] or versi[-1:]

    out = ["[Verse]"]
    out += strofe
    # se il testo e' lungo, una seconda strofa
    if len(resto) > 4:
        out.append("")
        out.append("[Verse 2]")
        out += resto[:len(resto) // 2]
        resto = resto[len(resto) // 2:]
    out.append("")
    out.append("[Chorus]")
    out += resto
    return "\n".join(out)


# --------------------------------------------------------------------------
# Il client Suno
# --------------------------------------------------------------------------

def _percorso_base() -> str:
    v = (__import__("os").environ.get("SUNO_API_URL", "") or "").strip()
    return v.rstrip("/") if v else "http://localhost:8000"


def _cookie() -> str:
    """Il cookie di sessione di suno.com (mai nei secrets: file locale)."""
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     ".suno_cookie.txt")
    try:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return f.read().strip()
    except Exception:
        pass
    return (__import__("os").environ.get("SUNO_COOKIE", "") or "").strip()


def _headers() -> dict:
    h = {"Content-Type": "application/json"}
    c = _cookie()
    if c:
        h["Cookie"] = c
    return h


def suno_disponibile() -> tuple[bool, str]:
    """Controlla che il servizio open source sia vivo."""
    if requests is None:
        return False, "requests non installato"
    try:
        r = requests.get(f"{_percorso_base()}/api/v1/health", timeout=12)
        if r.status_code == 200:
            return True, ""
        return False, f"servizio Suno non risponde ({r.status_code})"
    except Exception as exc:
        return False, (f"servizio Suno non raggiungibile su "
                       f"{_percorso_base()}: {str(exc)[:90]}")


def genera_canzone_suno(lyrics: str, tags: str = "", titolo: str = "",
                       timeout: int = 480, attendo: bool = True) -> dict:
    """
    Genera il cantico con Suno (crediti gratuiti del tuo account).

    Restituisce {"ok": True, "file": "<mp3>", "url": "...", "motore": "Suno"}
    oppure {"ok": False, "errore": "..."}
    """
    vuoto = {"ok": False, "errore": "", "file": "", "url": "",
             "motore": "Suno"}
    if requests is None:
        return {**vuoto, "errore": "requests non installato"}

    lyrics = struttura_canzone(lyrics)
    if len(lyrics) < 10:
        return {**vuoto, "errore": "Il testo del brano e' troppo corto."}

    tags = tags or TUTTI_I_TAG
    titolo = (titolo or "CANTICO")[:80]

    base = _percorso_base()
    # 1) il servizio e' vivo?
    ok, nota = suno_disponibile()
    if not ok:
        return {**vuoto, "errore": nota}

    # 2) chiedi la generazione
    try:
        r = requests.post(
            f"{base}/api/v1/generate",
            json={
                "prompt": lyrics,
                "tags": tags,
                "title": titolo,
                "make_instrumental": False,
                "wait_audio": bool(attendo),
            },
            headers=_headers(),
            timeout=timeout,
        )
    except Exception as exc:
        return {**vuoto, "errore": f"Suno non ha risposto: {str(exc)[:180]}"}

    if r.status_code == 401:
        return {**vuoto, "errore": ("Suno: cookie non valido. Rigenera il "
                                   "cookie di suno.com e mettilo in "
                                   ".suno_cookie.txt")}
    if r.status_code == 402:
        return {**vuoto, "errore": ("Suno: crediti giornalieri esauriti. "
                                   "aspetta domani o ricarica")}
    if r.status_code != 200:
        return {**vuoto, "errore": f"Suno errore {r.status_code}: {r.text[:180]}"}

    try:
        dati = r.json()
    except Exception:
        return {**vuoto, "errore": "risposta Suno non leggibile"}

    # 3) gli indici dei brani generati
    _data = dati.get("data") or {}
    _ids = _data.get("ids") or []
    _urls = _data.get("audio_urls") or []
    if not _urls and _ids:
        _urls = _attendi_suno(base, _ids, timeout)
    if not _urls:
        return {**vuoto, "errore": ("Suno non ha restituito l'audio. "
                                   "Puo' dipendere dalla coda: riprova.")}

    # 4) scarica il primo brano
    url_audio = _urls[0]
    try:
        out = os.path.join(tempfile.gettempdir(),
                           f"suno_{uuid.uuid4().hex[:10]}.mp3")
        rr = requests.get(url_audio, stream=True, timeout=240)
        if rr.status_code != 200:
            return {**vuoto, "errore": f"download non riuscito ({rr.status_code})"}
        with open(out, "wb") as f:
            for pezzo in rr.iter_content(65536):
                if pezzo:
                    f.write(pezzo)
    except Exception as exc:
        return {**vuoto, "errore": f"download fallito: {exc}"}

    return {"ok": True, "errore": "", "file": out, "url": url_audio,
            "motore": "Suno (i tuoi crediti gratuiti)"}


def _attendi_suno(base: str, ids: list, timeout: int) -> list:
    """Aspetta che i brani siano pronti e restituisce gli url."""
    scaduto = time.time() + timeout
    while time.time() < scaduto:
        time.sleep(8)
        try:
            r = requests.get(f"{base}/api/v1/get",
                             params={"ids": ",".join(map(str, ids))},
                             headers=_headers(), timeout=45)
            d = r.json()
        except Exception:
            continue
        _data = d.get("data") or []
        url = ""
        for brano in _data:
            if isinstance(brano, dict):
                for _k, _v in brano.items():
                    if isinstance(_v, str) and _v.endswith(".mp3"):
                        url = _v
                        break
            if url:
                break
            if isinstance(brano, str) and brano.endswith(".mp3"):
                url = brano
                break
        if url:
            return [url]
    return []
