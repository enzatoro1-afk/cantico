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
