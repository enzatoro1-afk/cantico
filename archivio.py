# -*- coding: utf-8 -*-
"""
archivio.py
===========
Archivio privato dei post preparati.

Ogni utente ha il PROPRIO archivio, identificato in automatico dal browser
(cookie "cantico_uid"): nessuno deve creare o ricordare nessun codice.
I file sono separati per identificatore, cosi' due persone che usano la
stessa app non vedono i post dell'altra. Un "codice archivio" puo' essere
aggiunto a mano solo se si vuole ritrovare i propri post su un altro
dispositivo.

Come funziona:
  - il codice personale -> hash SHA-256 -> nome file `archivio_<hash>.json`
  - l'hash non contiene il codice in chiaro: dal nome del file non si
    ricava il codice (e il codice non finisce nel file)
  - senza codice l'archivio NON viene salvato su disco: resta solo nella
    sessione del browser (e sparisce chiudendo il browser)
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime

SUFFISSO = ".json"


def _hash_codice(codice: str) -> str:
    """Codice -> identificatore anonimo del file (il codice resta segreto)."""
    return hashlib.sha256(("cantico-archivio:" + str(codice or "").strip())
                          .encode("utf-8")).hexdigest()[:20]


def _percorso(codice: str) -> str | None:
    """Percorso del file archivio per quel codice (None se non c'e' codice)."""
    if not (codice or "").strip():
        return None
    base = os.path.dirname(os.path.abspath(__file__))
    nome = f"archivio_{_hash_codice(codice)}{SUFFISSO}"
    percorso = os.path.join(base, nome)
    try:  # il filesystem del container potrebbe non essere scrivibile
        with open(percorso, "a", encoding="utf-8"):
            pass
        return percorso
    except Exception:
        return os.path.join(tempfile.gettempdir(), nome)


def carica_archivio(codice: str = "") -> list[dict]:
    """Legge l'archivio di QUEL codice. Se non c'e' -> lista vuota."""
    percorso = _percorso(codice)
    if not percorso:
        return []
    try:
        with open(percorso, "r", encoding="utf-8") as f:
            dati = json.load(f)
        if isinstance(dati, list):
            return dati
    except Exception:
        pass
    return []


def salva_archivio(voci: list[dict], codice: str = "") -> bool:
    """Salva l'archivio di QUEL codice. True se la scrittura e' riuscita."""
    percorso = _percorso(codice)
    if not percorso:
        return False
    try:
        with open(percorso, "w", encoding="utf-8") as f:
            json.dump(voci, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def aggiungi_post(post: dict, codice: str = "",
                 voci_correnti: list[dict] | None = None) -> list[dict]:
    """
    Aggiunge un post all'archivio di QUEL codice (in cima) e lo persiste.
    Il post riceve un id e la data di creazione.

    voci_correnti: se passato, si usa quella lista come base invece di
    leggere il file. Serve quando non c'e' un codice: in quel caso
    l'archivio vive solo nella sessione del browser e NON va su disco.
    """
    if voci_correnti is not None:
        voci = list(voci_correnti)
    else:
        voci = carica_archivio(codice)
    nuovo = dict(post)
    nuovo.setdefault("id", datetime.now().strftime("%Y%m%d%H%M%S%f"))
    nuovo.setdefault("creato_il", datetime.now().strftime("%d/%m/%Y %H:%M"))
    voci.insert(0, nuovo)
    if codice:
        salva_archivio(voci, codice)
    return voci


def elimina_post(post_id: str, codice: str = "") -> list[dict]:
    """Rimuove un post dall'archivio di QUEL codice e lo persiste."""
    voci = [v for v in carica_archivio(codice) if v.get("id") != post_id]
    salva_archivio(voci, codice)
    return voci


def cancella_archivio(codice: str = "") -> bool:
    """Cancella TUTTO l'archivio di quel codice (file compreso)."""
    percorso = _percorso(codice)
    if not percorso:
        return False
    try:
        if os.path.exists(percorso):
            os.remove(percorso)
        return True
    except Exception:
        return False
