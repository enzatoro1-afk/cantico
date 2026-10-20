# -*- coding: utf-8 -*-
"""
post_generator.py
=================
Genera il "pacchetto di pubblicazione" per TikTok a partire dal testo
inserito: caption, hashtag, testo da mettere a schermo (hook) e link utili.

Nota sulla pubblicazione automatica:
  TikTok non permette a una web app personale e gratuita di pubblicare video
  in automatico. Serve la Content Posting API ufficiale, che richiede un
  account sviluppatore, la registrazione di un'app e l'approvazione di TikTok
  (mesi di iterazione). Quindi qui prepariamo TUTTO il materiale e l'utente
  pubblica con un tocco su TikTok: il pulsante "Apri TikTok" + il testo già
  copiato nel clipboard.
"""

from __future__ import annotations

import re
from urllib.parse import quote_plus

from text_tools import senza_accenti

FORMATI_POST = (
    "Versetto + domanda",
    "Versetto + invito alla reflection",
    "Frase d'impatto",
    "Solo versetto",
)

HASHTAG_BASE = [
    "#fede",
    "#lode",
    "#cristianitiktok",
    "#inno",
    "#gospel",
    "#vita",
]

# Hashtag tematici attivati in base alle parole chiave del testo
HASHTAG_TEMATICI = {
    "pentecoste": ["#pentecoste", "#spiritosanto"],
    "pentecostale": ["#pentecoste", "#spiritosanto"],
    "spirito": ["#spirito", "#spiritosanto"],
    "amore": ["#amoredidio", "#dionostriamo"],
    "grazia": ["#grazia", "#graziedio"],
    "perdono": ["#perdono", "#riconciliazione"],
    "gioia": ["#gioia", "#allelujia"],
    "salvezza": ["#salvezza", "#cristoesalvatore"],
    "preghiera": ["#preghiera", "#orazione"],
    "adorazione": ["#adorazione", "#worship"],
    "praise": ["#praise", "#worship"],
    "guarigione": ["#guarigione", "#fede"],
    "ansia": ["#ansia", "#pace"],
    "pace": ["#pace", "#serenita"],
}

APERTURE = (
    "Fermati un secondo \U0001F4D6",
    "Questa frase ti ha fatto pensare?\U0001F914",
    "Ascolta questo prima di scorrere \U0001F50A",
    "Se hai bisogno di una parola oggi, è qui \U0001F64F",
    "Non scorrere troppo veloce \U0001F645",
)

CHIUSURE = (
    "Scrivi nei commenti cosa ti ha toccato \U0001F4AC",
    "Salva questo video per quando ne avrai bisogno \U0000D83D\uDCCB",
    "Tagga chi ha bisogno di sentire questo \U0001F517",
    "Condividi per ricevere una parola \U0001F49B",
    "Dillo a Dio, anche solo in silenzio \U0001F5E8",
)


def _pulisci(testo: str) -> str:
    """Pulisce il testo: spazi multipli, a capo, virgolette strane."""
    testo = re.sub(r"\s+", " ", (testo or "").strip())
    return testo


def genera_hashtag(testo: str, parole_chiave: list[str] | None = None) -> list[str]:
    """Crea un set di hashtag: base + tematici in base al contenuto del testo."""
    bag = " ".join(parole_chiave or []) + " " + senza_accenti(testo)
    risultati = list(HASHTAG_BASE)
    for chiave, tag in HASHTAG_TEMATICI.items():
        if chiave in bag:
            for t in tag:
                if t not in risultati:
                    risultati.append(t)
    # limite: TikTok mostra bene 3-6 hashtag
    return risultati[:7]


def genera_hook(testo: str) -> str:
    """Testo da mostrare a schermo nei primi secondi (max 6 parole)."""
    testo = _pulisci(testo)
    parole = testo.split()
    if not parole:
        return "Fermati un secondo \U0001F4D6"
    if len(parole) <= 6:
        return testo
    return " ".join(parole[:6])


def genera_caption(testo: str, formato: str, hashtag: list[str] | None = None,
                   rng=None) -> str:
    """
    Costruisce la caption pronta per essere incollata su TikTok.
    """
    testo = _pulisci(testo)
    hashtag = hashtag or []
    stringa_hashtag = " ".join(hashtag)
    import random
    rng = rng or random

    if formato == "Solo versetto":
        return f'"{testo}"\n\n{stringa_hashtag}'.strip()

    if formato == "Frase d'impatto":
        apertura = rng.choice(APERTURE)
        chiusura = rng.choice(CHIUSURE)
        return f"{apertura}\n\n\"{testo}\"\n\n{chiusura}\n\n{stringa_hashtag}".strip()

    if formato == "Versetto + invito alla reflection":
        chiusura = rng.choice(CHIUSURE)
        return (
            f'"{testo}"\n\n'
            "Fermati e lascia che questa parola lavori dentro di te \U0001F64C\n\n"
            f"{chiusura}\n\n{stringa_hashtag}"
        ).strip()

    # predefinito: Versetto + domanda
    domande = (
        "Cosa dice questo a te, oggi? \U0001F4AC",
        "Dove ti incontri con questa parola? \U0001F4AC",
        "Questo è il tuo versetto di oggi? \U0001F4AC",
    )
    return (
        f'"{testo}"\n\n'
        f"{rng.choice(domande)}\n\n"
        f"{stringa_hashtag}"
    ).strip()


def pacchetto_pubblicazione(testo: str, formato: str,
                            parole_chiave: list[str] | None = None) -> dict:
    """Restituisce l'intero pacchetto pronto all'uso."""
    testo = _pulisci(testo)
    hashtag = genera_hashtag(testo, parole_chiave)
    return {
        "caption": genera_caption(testo, formato, hashtag),
        "hashtag": hashtag,
        "hashtag_string": " ".join(hashtag),
        "hook": genera_hook(testo),
        "testo": testo,
    }


# --------------------------------------------------------------------------
# Data e orario di pubblicazione
# --------------------------------------------------------------------------

GIORNI_SETTIMANA = ["lunedì", "martedì", "mercoledì", "giovedì",
                     "venerdì", "sabato", "domenica"]


def giorno_settimana(data) -> str:
    """Nome del giorno in italiano (data = datetime.date)."""
    try:
        return GIORNI_SETTIMANA[data.weekday()]
    except Exception:
        return ""


def suggerisci_orari(data) -> list[dict]:
    """
    Orari consigliati per pubblicare un contenuto religioso, in base al giorno.
    Ritorna [{"orario": "07:00", "motivo": "..."}, ...]
    """
    try:
        weekday = data.weekday()
    except Exception:
        weekday = 0

    orari = [
        {"orario": "07:00",
         "motivo": "mattina presto: momento di preghiera e di contemplazione"},
        {"orario": "12:30",
         "motivo": "pausa pranzo: picco di scroll, momento di riscontro"},
        {"orario": "20:30",
         "motivo": "sera: fascia con la massima attenzione sulle piattaforme"},
    ]

    if weekday == 6:  # domenica
        orari.insert(0, {"orario": "08:30",
                         "motivo": "domenica mattina: molti ascoltano un inno "
                                   "prima della messa"})
    if weekday in (2, 4):  # mercoledì e venerdì
        orari.insert(1, {"orario": "19:30",
                         "motivo": "serata di preghiera / adunanza: momento perfetto"})
    if weekday == 5:  # sabato
        orari.append({"orario": "11:00",
                      "motivo": "sabato mattina: le persone condividono di più"})
    return orari


def link_tiktok_upload(caption: str = "") -> str:
    """Link che apre l'area di caricamento di TikTok (l'app, se installata)."""
    base = "https://www.tiktok.com/upload"
    if caption:
        return f"{base}?caption={quote_plus(caption[:150])}"
    return base


def link_tiktok_ricerca_audio(titolo: str) -> str:
    """Link che apre la ricerca audio di TikTok per un titolo."""
    return f"https://www.tiktok.com/music?q={quote_plus(titolo)}"
