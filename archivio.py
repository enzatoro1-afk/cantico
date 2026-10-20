# -*- coding: utf-8 -*-
"""
archivio.py
===========
Archivio persistente dei post preparati.

Tutti i pacchetti post (testo, canzone, caption, hashtag, data di
pubblicazione) vengono salvati in un file JSON nella cartella dell'app,
così restano disponibili anche dopo aver chiuso il browser.

Su Streamlit Community Cloud il file vive nel container: resta valido per
tutta la sessione del servizio. Se il filesystem non è scrivibile
(situazione possibile in alcuni hosting), l'archivio continua a funzionare
in memoria per la sessione corrente.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime

NOME_FILE = "archivio_post.json"

PERCORSO = os.path.join(os.path.dirname(os.path.abspath(__file__)), NOME_FILE)


def _percorso() -> str:
    """Percorso del file, con fallback su una cartella temporanea scrivibile."""
    try:
        with open(PERCORSO, "a", encoding="utf-8"):
            pass
        return PERCORSO
    except Exception:
        return os.path.join(tempfile.gettempdir(), NOME_FILE)


def carica_archivio() -> list[dict]:
    """Legge l'archivio dal file. Se non esiste o è corrotto -> lista vuota."""
    try:
        with open(_percorso(), "r", encoding="utf-8") as f:
            dati = json.load(f)
        if isinstance(dati, list):
            return dati
    except Exception:
        pass
    return []


def salva_archivio(voci: list[dict]) -> bool:
    """Salva l'archivio su disco. Ritorna True se la scrittura è riuscita."""
    try:
        with open(_percorso(), "w", encoding="utf-8") as f:
            json.dump(voci, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def aggiungi_post(post: dict) -> list[dict]:
    """
    Aggiunge un post all'archivio (in cima) e lo persiste.
    Il post riceve un id e la data di creazione.
    """
    voci = carica_archivio()
    nuovo = dict(post)
    nuovo.setdefault("id", datetime.now().strftime("%Y%m%d%H%M%S%f"))
    nuovo.setdefault("creato_il", datetime.now().strftime("%d/%m/%Y %H:%M"))
    voci.insert(0, nuovo)
    salva_archivio(voci)
    return voci


def elimina_post(post_id: str) -> list[dict]:
    """Rimuove un post dall'archivio e lo persiste."""
    voci = [v for v in carica_archivio() if v.get("id") != post_id]
    salva_archivio(voci)
    return voci
