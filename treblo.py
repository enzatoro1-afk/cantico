# -*- coding: utf-8 -*-
"""
treblo.py
=========
Motore musicale "Treblo" (ex Sonauto): testo -> canzone CANTATA, con API
ufficiale e 3.000 crediti gratuiti al primo uso.

Perche' e' il motore piu' comodo dell'app:
  - la API e' documentata e semplice (una POST, un poll, un download)
  - l'audio che torna e' un file vero (mp3): l'app lo scarica e ci fa
    sopra il video .mp4, senza passaggi manuali e senza cifrature
  - 3.000 crediti gratis con l'account nuovo (100 crediti a canzone)

COME SI USA:
  1) crea l'account su https://treblo.com e prendi la chiave API
     (la trovi nella pagina /developers/account)
  2) incollala nell'app, nella barra laterale, campo
     "Chiave Treblo (facoltativa)"
  3) nell'app scegli il motore "Treblo (crediti gratis)" e premi
     "Componi e canta la canzone"

La chiave resta nel tuo browser / nel file locale: non finisce su GitHub.
"""

from __future__ import annotations

import os
import tempfile
import time
import uuid

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore

API = "https://api.treblo.com/v1"

# i tag di stile che CANTANO bene per un inno (glieli mettiamo noi)
TAG_GOSPEL = [
    "gospel/christian",
    "contemporary gospel",
    "piano",
    "acoustic guitar",
    "warm vocal",
    "inspiring",
    "uplifting",
    "emotional",
]


def _percorso_chiave_server() -> str:
    """Il file con la chiave condivisa (sul server, per tutti)."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        ".chiave_treblo_server.json")


def ricorda_chiave(chiave: str) -> bool:
    """
    Salva la chiave sul server, cosi' non va reinserita a ogni sessione
    (vale per TUTTI gli utenti dell'app). Il file NON e' su GitHub.
    """
    chiave = (chiave or "").strip()
    if not chiave:
        return False
    try:
        import json
        with open(_percorso_chiave_server(), "w", encoding="utf-8") as f:
            json.dump({"TREBLO_API_KEY": chiave}, f)
        return True
    except Exception:
        return False


def dimentica_chiave() -> bool:
    """Cancella la chiave condivisa sul server."""
    try:
        p = _percorso_chiave_server()
        if os.path.exists(p):
            os.remove(p)
            return True
    except Exception:
        pass
    return False


def _chiave() -> str:
    """La chiave API: dalla barra laterale, dai secrets o dall'ambiente."""
    try:
        import streamlit as st
        v = str(st.session_state.get("chiave_treblo", "") or "").strip()
        if v:
            return v
    except Exception:
        pass
    for nome in ("TREBLO_API_KEY", "SONAUTO_API_KEY"):
        # i Secrets di Streamlit (la chiave dell'app, per tutti)
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
        import tomllib
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         ".streamlit", "secrets.toml")
        if os.path.exists(p):
            with open(p, "rb") as f:
                d = tomllib.load(f)
            for nome in ("TREBLO_API_KEY", "SONAUTO_API_KEY"):
                v = str(d.get(nome, "") or "").strip()
                if v:
                    return v
    except Exception:
        pass
    # la chiave condivisa sul server (per tutti)
    try:
        import json
        p = _percorso_chiave_server()
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                d = json.load(f)
            v = str(d.get("TREBLO_API_KEY", "") or "").strip()
            if v:
                return v
    except Exception:
        pass
    return ""


def _headers() -> dict:
    return {"Authorization": f"Bearer {_chiave()}",
            "Content-Type": "application/json"}


def treblo_disponibile() -> tuple:
    """Controlla la chiave e dice quanti crediti restano."""
    if requests is None:
        return False, "requests non installato"
    if not _chiave():
        return False, ("manca la chiave Treblo (gratis): prendila su "
                       "treblo.com -> account sviluppatore")
    try:
        r = requests.get(f"{API}/credits/balance", headers=_headers(), timeout=25)
        if r.status_code == 200:
            d = r.json() or {}
            crediti = d.get("num_credits")
            if crediti is None:
                crediti = d.get("credits", d.get("balance"))
            if not crediti:
                return True, ("Treblo attivo, ma SENZA crediti: attiva il "
                              "free trial nella scheda Plan (verifica la "
                              "carta: non ti vengono addebitati soldi)")
            return True, f"crediti Treblo rimasti: {crediti}"
        if r.status_code in (401, 403):
            return False, "chiave Treblo non valida"
        return False, f"Treblo non risponde ({r.status_code})"
    except Exception as exc:
        return False, f"impossibile contattare Treblo: {str(exc)[:80]}"


def genera_canzone_treblo(lyrics: str, tags: str = "", timeout: int = 420) -> dict:
    """
    Genera il brano cantato con Treblo e scarica l'audio (mp3).

    Restituisce {"ok": True, "file": "<mp3>", "url": "...", "motore": "Treblo"}
    oppure {"ok": False, "errore": "..."}
    """
    vuoto = {"ok": False, "errore": "", "file": "", "url": "", "motore": "Treblo"}
    if requests is None:
        return {**vuoto, "errore": "requests non installato"}
    if not _chiave():
        return {**vuoto, "errore": (
            "Manca la chiave Treblo: prendila gratis su treblo.com "
            "(account sviluppatore) e incollala nel campo 'Chiave Treblo' "
            "qui sopra (o nella barra laterale).")}

    lyrics = (lyrics or "").strip()
    if len(lyrics) < 10:
        return {**vuoto, "errore": "Il testo del brano e' troppo corto."}

    # i tag: quelli dell'app + i nostri per il canto
    _tag = list(TAG_GOSPEL)
    for t in str(tags or "").replace(";", ",").split(","):
        t = t.strip()
        if t and t.lower() not in [x.lower() for x in _tag]:
            _tag.append(t)
    _tag = _tag[:12]

    corpo = {
        "lyrics": lyrics[:2900],
        "tags": _tag,
        "instrumental": False,
        "output_format": "mp3",
        "output_bit_rate": 192,
        "length_range": [30, 90],
    }
    try:
        r = requests.post(f"{API}/generations/v3", json=corpo,
                          headers=_headers(), timeout=60)
    except Exception as exc:
        return {**vuoto, "errore": f"Treblo non ha risposto: {str(exc)[:140]}"}

    if r.status_code in (401, 403):
        return {**vuoto, "errore": ("Treblo: chiave non valida (o crediti "
                                   "esauriti).")}
    if r.status_code == 402:
        return {**vuoto, "errore": ("Treblo: crediti esauriti. Sono gratis "
                                   "al primo accesso: 3.000 crediti = 30 "
                                   "canzoni.")}
    if r.status_code != 200:
        return {**vuoto, "errore": f"Treblo errore {r.status_code}: "
                                   f"{r.text[:150]}"}
    try:
        task = (r.json() or {}).get("task_id")
    except Exception:
        task = ""
    if not task:
        return {**vuoto, "errore": "Treblo non ha restituito il brano"}

    # 2) aspetto che sia pronto
    scaduto = time.time() + timeout
    stato = ""
    while time.time() < scaduto:
        time.sleep(5)
        try:
            s = requests.get(f"{API}/generations/status/{task}",
                             headers=_headers(), timeout=30)
            if s.status_code != 200:
                continue
            stato = str((s.json() or {}).get("status", ""))
        except Exception:
            continue
        if stato == "SUCCESS":
            break
        if stato == "FAILURE":
            return {**vuoto, "errore": "Treblo: generazione fallita"}

    if stato != "SUCCESS":
        return {**vuoto, "errore": ("Treblo: il brano non e' pronto in tempo "
                                    "(stato: " + (stato or "?") + "). Riprova.")}

    # 3) l'indirizzo del file
    try:
        g = requests.get(f"{API}/generations/{task}", headers=_headers(),
                         timeout=45)
        d = g.json() or {}
        _percorsi = d.get("song_paths") or []
        if not _percorsi:
            return {**vuoto, "errore": "Treblo: il brano e' pronto ma non ha "
                                       "restituito il file"}
        url_audio = str(_percorsi[0])
    except Exception as exc:
        return {**vuoto, "errore": f"Treblo: non riesco a prendere il file: "
                                   f"{str(exc)[:120]}"}

    # 4) scarico l'audio
    try:
        out = os.path.join(tempfile.gettempdir(),
                           f"treblo_{uuid.uuid4().hex[:10]}.mp3")
        rr = requests.get(url_audio, stream=True, timeout=300)
        if rr.status_code != 200:
            return {**vuoto, "errore": f"download non riuscito "
                                       f"({rr.status_code})"}
        _tot = 0
        with open(out, "wb") as f:
            for pezzo in rr.iter_content(65536):
                if pezzo:
                    f.write(pezzo)
                    _tot += len(pezzo)
        if _tot < 10000:
            os.remove(out)
            return {**vuoto, "errore": "Treblo: il file audio e' vuoto"}
    except Exception as exc:
        return {**vuoto, "errore": f"download fallito: {exc}"}

    return {"ok": True, "errore": "", "file": out, "url": url_audio,
            "motore": "Treblo (crediti gratis)"}
