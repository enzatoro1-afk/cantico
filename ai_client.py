# -*- coding: utf-8 -*-
"""
ai_client.py
============
Chiamata diretta a un'IA (OpenAI / compatibili) per l'interpretazione
dottrinale del versetto.

E' FACOLTATIVO: senza chiave API l'app continua a funzionare con il motore
"predicazioni reali" (trascrizioni YouTube dei ministri/pastori evangelici).
"""

from __future__ import annotations

import json

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore

MODEL_PREDEFINITO = "gpt-4o-mini"
URL_PREDEFINITO = "https://api.openai.com/v1/chat/completions"


def chiave_da_secrets() -> str:
    """Cerca la chiave nelle secrets di Streamlit (se configurate)."""
    try:
        import streamlit as st
        return (st.secrets.get("OPENAI_API_KEY", "") or "").strip()
    except Exception:
        return ""


def interpreta_con_ia(prompt: str, chiave: str = "", modello: str = "",
                       url_api: str = "", timeout: int = 90) -> dict:
    """
    Invia il prompt all'IA e restituisce:
      {"testo": "...", "parole_chiave": [...], "errore": None|str,
       "modello": "...", "fonte": "ChatGPT (API)"}

    Se manca la chiave o la rete fallisce, NON solleva: restituisce
    l'errore nel dizionario, così l'app può ripiegare sul motore YouTube.
    """
    if requests is None:
        return {"testo": "", "parole_chiave": [], "errore": "requests non installato",
                "modello": "", "fonte": "ChatGPT (API)"}

    chiave = (chiave or chiave_da_secrets() or "").strip()
    if not chiave:
        return {"testo": "", "parole_chiave": [],
                "errore": "Nessuna chiave API: aggiungila nella casella "
                          "'Chiave API OpenAI' in alto.",
                "modello": "", "fonte": "ChatGPT (API)"}

    modello = modello or MODEL_PREDEFINITO
    url_api = url_api or URL_PREDEFINITO

    corpo = {
        "model": modello,
        "messages": [
            {"role": "system",
             "content": "Sei un assistente biblico di dottrina Cristiana "
                        "Evangelica Pentecostale (linea ADI / Assemblee di Dio). "
                        "Rispondi in italiano, con titoli chiari, senza "
                        "preamboli. NON citare canzoni, inni o titoli di "
                        "brani: curi solo il significato del testo."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.4,
        "max_tokens": 1600,
    }

    try:
        risposta = requests.post(
            url_api,
            headers={"Authorization": f"Bearer {chiave}",
                     "Content-Type": "application/json"},
            data=json.dumps(corpo).encode("utf-8"),
            timeout=timeout,
        )
        if risposta.status_code != 200:
            return {"testo": "", "parole_chiave": [],
                    "errore": f"IA: errore {risposta.status_code} "
                              f"({risposta.text[:180]})",
                    "modello": modello, "fonte": "ChatGPT (API)"}
        dati = risposta.json()
        testo = (dati["choices"][0]["message"]["content"] or "").strip()
        return {"testo": testo, "parole_chiave": [], "errore": None,
                "modello": modello, "fonte": f"ChatGPT ({modello})"}
    except Exception as exc:
        return {"testo": "", "parole_chiave": [],
                "errore": f"IA non raggiungibile: {exc}",
                "modello": modello, "fonte": "ChatGPT (API)"}


def link_chatgpt(prompt: str) -> str:
    """Link che apre ChatGPT con il prompt gia' scritto (web app)."""
    from urllib.parse import quote_plus
    return "https://chatgpt.com/?q=" + quote_plus(prompt)


# --------------------------------------------------------------------------
# IA GRATUITA SENZA CHIAVE API
# --------------------------------------------------------------------------
# Pollinations AI: risponde senza registrazione e senza chiave.
# Limite: 1 risposta ogni ~30 secondi per IP (si risolve aspettando e
# riprovare). Se fallisce l'app ripiega sul motore di studio.

URL_POLLINATIONS = "https://text.pollinations.ai/"
MODELLO_POLLINATIONS = "openai"

SISTEMA_BIBLICO = (
    "Sei un teologo evangelico pentecostale (linea ADI / Assemblee di Dio). "
    "Rispondi in ITALIANO, con titoli in grassetto e senza preamboli.\n"
    "REGOLE FONDAMENTALI (non violarle):\n"
    "1) Parti SEMPRE e SOLO dal testo biblico che ti do: spiega QUEL testo, "
    "non un altro. Non citare altri versetti come se fossero il soggetto.\n"
    "2) NON INVENTARE MAI. In particolare:\n"
    "   - usa i nomi ESATTAMENTE come compaiono nel testo (se il testo dice "
    "'Gesù', scrivi 'Gesù', non un altro nome);\n"
    "   - non aggiungere luoghi, persone, eventi, numeri o dettagli che non "
    "sono nel testo;\n"
    "   - se non sai qualcosa, non scriverlo.\n"
    "3) Non citare canzoni, inni o titoli di brani musicali.\n"
    "4) Scrivi in modo che si possa cantare: parole semplici, cuore, "
    "affidamento a Dio, speranza, coraggio.\n"
    "5) Non troncare la risposta: scrivi tutte e 4 le sezioni, ma brevi "
    "(massimo 2-3 frasi per sezione)."
)


def _pulisci_giornale(testo: str) -> str:
    """
    Se la risposta e' stata troncata a meta' frase, la riporta all'ultima
    frase completa (meglio una risposta un po' piu' corta che una parola
    mozzata).
    """
    t = (testo or "").strip()
    if not t:
        return t
    # se finisce con un carattere di punteggiatura, e' completa
    if t[-1] in ".!?;:)\"'":
        return t
    # cerco l'ultimo punto/virgola "forte" e taglio li'
    for sep in (". ", ".\n", "! ", "? "):
        idx = t.rfind(sep)
        if idx > len(t) * 0.4:
            return t[:idx + 1].strip()
    # niente: taglio all'ultima newline
    idx = t.rfind("\n")
    if idx > len(t) * 0.4:
        return t[:idx].strip()
    return t


def interpreta_gratis(prompt: str, timeout: int = 120,
                      tentativi: int = 3) -> dict:
    """
    Chiede l'interpretazione a una IA GRATUITA che non richiede chiave API.

    Restituisce: {"testo": ..., "parole_chiave": [...], "errore": None|str,
                  "modello": ..., "fonte": ...}
    Non solleva mai: se fallisce, l'errore torna nel dizionario e l'app
    ripiega sul motore di studio.
    """
    vuoto = {"testo": "", "parole_chiave": [], "modello": "",
             "fonte": "IA gratuita"}
    if requests is None:
        return {**vuoto, "errore": "requests non installato"}

    import time

    ultimo_errore = ""
    for tentativo in range(max(1, tentativi)):
        try:
            risposta = requests.post(
                URL_POLLINATIONS,
                json={
                    "model": MODELLO_POLLINATIONS,
                    "messages": [
                        {"role": "system", "content": SISTEMA_BIBLICO},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 2500,
                },
                timeout=timeout,
                headers={"User-Agent": "Mozilla/5.0 (compatible; CANTICO/1.0)"},
            )
            if risposta.status_code == 200:
                testo = _pulisci_giornale(risposta.text or "")
                if len(testo) > 120:
                    return {
                        "testo": testo,
                        "parole_chiave": [],
                        "errore": None,
                        "modello": MODELLO_POLLINATIONS,
                        "fonte": "IA gratuita (Pollinations)",
                    }
                ultimo_errore = "risposta troppo corta"
            elif risposta.status_code == 402:
                ultimo_errore = ("servizio gratuito troppo richiesto "
                                  "(attendo e riprovo)")
            else:
                ultimo_errore = (f"errore {risposta.status_code}: "
                                 f"{risposta.text[:120]}")
        except Exception as exc:
            ultimo_errore = f"IA non raggiungibile: {exc}"

        if tentativo < tentativi - 1:
            time.sleep(32)   # il limite e' 1 risposta ogni 30 secondi

    return {**vuoto, "errore": ultimo_errore or "IA gratuita non disponibile"}
