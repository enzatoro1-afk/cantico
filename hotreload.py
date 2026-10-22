# -*- coding: utf-8 -*-
"""
hotreload.py
============
Ricarica i moduli locali del progetto quando i loro file cambiano.

Perche' serve:
    Streamlit riesegue solo `app.py` a ogni interazione, ma i moduli
    importati restano in `sys.modules`: se cambi `youtube_search.py` e
    riavvii la pagina, il codice VECchio continua a girare.
    Lo stesso vale su Streamlit Cloud quando un deploy riusa il processo.

Come funziona:
    - per ogni modulo teniamo l'mtime del file sorgente
    - se l'mtime e' cambiato -> `importlib.reload(modulo)`
    - l'ordine di ricarica rispetta le dipendenze (prima i 'mattoni')

Il dizionario `STATI` vive in questo modulo, che non viene mai
ricaricato: cosi' i mtime restano noti fra un'esecuzione e l'altra.
"""

from __future__ import annotations

import importlib
import os
import sys

# ordine rispettando le dipendenze (i 'mattoni' prima)
ORDINE = (
    "text_tools",
    "bible_search",
    "bible_search2",
    "studio_biblico",
    "youtube_search",
    "post_generator",
    "tiktok_sounds",
    "ai_client",
    "archivio",
    "accesso",
    # moduli aggiunti dopo: senza questi, il server teneva in memoria la
    # versione VECCHIA e l'app si rompeva con un AttributeError
    "riflessione",
    "setup_app",
    "tiktok_pubblica",
)

# mtime noto per ciascun modulo (vive nel namespace di questo modulo)
STATI: dict[str, float] = {}


def _percorso(nome: str) -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        nome + ".py")


def ricarica(extra: tuple[str, ...] = ()) -> list[str]:
    """
    Ricarica i moduli il cui file e' cambiato.
    Restituisce l'elenco dei moduli effettivamente ricaricati.
    """
    ricaricati: list[str] = []
    for nome in tuple(ORDINE) + tuple(extra):
        path = _percorso(nome)
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            continue
        if STATI.get(nome) == mtime:
            continue
        modulo = sys.modules.get(nome)
        if modulo is None:
            # non ancora importato: lo lascio importare normalmente
            STATI[nome] = mtime
            continue
        try:
            importlib.reload(modulo)
            STATI[nome] = mtime
            ricaricati.append(nome)
        except Exception:
            # se il reload fallisce lascio il modulo com'e' (non blocco l'app)
            STATI[nome] = mtime
    return ricaricati


def _modulo_fresco(nome: str):
    """
    Importa (o ricarica) un modulo del progetto, garantendo che sia la
    versione PIU' RECENTE del file.

    Serve per i moduli aggiunti dopo: senza questo, il server teneva in
    memoria la versione vecchia e l'app si rompeva (AttributeError).
    """
    import importlib
    try:
        _m = importlib.import_module(nome)
    except Exception:
        return None
    try:
        if os.path.exists(_percorso(nome)):
            importlib.reload(_m)
    except Exception:
        pass
    return _m


def build_piu_recente() -> str:
    """Data/ora del file piu' recente del progetto (per il timbro 'versione')."""
    piu = 0.0
    base = os.path.dirname(os.path.abspath(__file__))
    try:
        for nome in os.listdir(base):
            if nome.endswith(".py"):
                try:
                    piu = max(piu, os.path.getmtime(os.path.join(base, nome)))
                except OSError:
                    pass
    except OSError:
        pass
    try:
        piu = max(piu, os.path.getmtime(__file__))
    except OSError:
        pass
    return __import__("datetime").datetime.fromtimestamp(piu).strftime(
        "%Y-%m-%d %H:%M")


def versione() -> str:
    """
    Versione 'leggibile' del codice in esecuzione:
    VERSION.txt (scritto dallo script di push) + data del file piu' recente.
    """
    base = os.path.dirname(os.path.abspath(__file__))
    tag = ""
    try:
        with open(os.path.join(base, "VERSION.txt"), encoding="utf-8") as f:
            tag = f.read().strip()
    except OSError:
        tag = ""
    return f"{tag} · {build_piu_recente()}" if tag else build_piu_recente()
