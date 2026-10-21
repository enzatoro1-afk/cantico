"""
bible_search2.py
================
RICERCA LIBERA in tutta la Bibbia:
  - "genesi" -> il libro, con i suoi capitoli
  - "pastore" -> i passaggi che parlano di pastore, col testo completo
  - sotto: "cosa vuoi approfondire? (quali numeri)"
"""

from __future__ import annotations

import re

from bible_search import LIBRI_IT, motore
from text_tools import senza_accenti

# parole da scartare nella ricerca libera
STOP_RICERCA = {
    "dio", "signore", "gesu", "cristo", "santo", "santa",
    "e", "il", "lo", "la", "i", "gli", "le", "di", "che", "non", "per",
    "con", "sono", "come", "suo", "suoi", "mia", "mio", "del", "della",
    "a", "in", "un", "una", "io", "tu", "lui", "lei", "noi", "voi", "da",
    "ha", "hanno", "era", "questo", "questa", "quello", "quella", "piu",
    "poi", "ancora", "sempre", "mai", "anche", "ma", "se", "quando", "dove",
    "cosa", "tutti", "tutto", "ogni", "dei", "nel", "sulla", "dal", "dalla",
    "loro", "ti", "mi", "vi", "ci", "ne", "od", "o", "al", "alla", "ai",
    "alle", "ed", "affinche", "perche", "dove", "verso", "parola", "parole",
    "salmo", "salmi", "coro", "versetto", "versetti", "capitolo", "capitoli",
    "libro", "libri", "bibbia", "testo", "trova", "trovare", "cerca",
    "cercare", "vorrei", "voglio", "sapere", "parlare", "spiegare",
    "significato", "interpretazione", "vita", "cuore", "anima", "gente",
    "figli", "padre", "madre", "fratello", "sorella", "casa", "giorni",
    "opera", "parole", "manoscritto", "scrittura",
}

# parole -> come sono dette nella Bibbia (sinonimi, per non perdere i passaggi)
SINONIMI = {
    "pastore": ["pastore", "pascere", "pecora", "grege", "conductor"],
    "consolazione": ["consola", "consol", "conforto", "raccordo"],
    "misericordia": ["misericord", "pieta", "compassione"],
    "perdono": ["perdon", "remissione", "rimetti", "rimissioni"],
    "salvezza": ["salvezza", "salvatore", "salva", "redenz"],
    "speranza": ["speranza", "spera", "confida", "attendo"],
    "pace": ["pace", "pacifico", "quieto", "riposo"],
    "amore": ["amore", "ama", "diletto", "carita"],
    "abbandono": ["abbandon", "abbandonato"],
    "lode": ["lode", "loda", "lodate", "celebra", "magnifica", "esalta"],
    "grazia": ["grazia", "grazioso"],
    "coraggio": ["coraggio", "fortezza", "forti"],
    "peccato": ["peccato", "peccati", "colpa", "iniquita", "trasgressione"],
    "pentecoste": ["pentecoste", "spianto", "doni", "cenacolo"],
    "fede": ["fede", "credere", "crede"],
    "verita": ["verita", "vero", "testimoni"],
    "luce": ["luce", "lumen", "risplende"],
    "scrittura": ["scrittura", "legge", "comandamento", "statuto"],
    "tempesta": ["tempesta", "tempeste"],
    "mattino": ["mattina", "mattino"],
    "notte": ["notte", "notturno"],
    "cuore": ["cuore", "cuori"],
}


def _tokens(testo: str) -> list[str]:
    return [p for p in re.findall(r"[a-z]{3,}", senza_accenti(testo or ""))
            if p not in STOP_RICERCA]


def _prefissi(parola: str) -> list[str]:
    """Prefissi da cercare nell'indice (>= 4 lettere, niente falsi positivi)."""
    out = {parola[:4]}
    for chiave, valori in SINONIMI.items():
        if parola.startswith(chiave[:4]) or chiave.startswith(parola[:4]):
            for v in valori:
                if len(v) >= 4:
                    out.add(v[:4])
    return [p for p in out if len(p) >= 4]


def cerca_libri(nome: str) -> list[str]:
    """Libri della Bibbia il cui nome contiene il testo cercato."""
    n = senza_accenti(nome or "").strip()
    if len(n) < 2:
        return []
    risultati = []
    for libro in LIBRI_IT:
        l = senza_accenti(libro).lower()
        if n in l or l.startswith(n[:4]):
            if libro not in risultati:
                risultati.append(libro)
    return risultati


def capitoli_del(libro: str) -> list[int]:
    m = motore()
    return sorted({k[1] for k in m.versetti_per_capitolo if k[0] == libro})


def _versi_con(m, prefissi: list[str]) -> set[int]:
    trovati: set[int] = set()
    for chiave, idxs in m.indice.items():
        if len(chiave) >= 4 and any(chiave.startswith(p[:4]) for p in prefissi):
            trovati.update(idxs)
    return trovati


def cerca_passaggi(testo: str, contesto: int = 2, max_passaggi: int = 8) -> list[dict]:
    """
    Cerca un testo in tutta la Bibbia e restituisce i PASSAGGI (blocchi di
    versetti contigui) col testo completo del paragrafo.
    """
    parole = _tokens(testo)
    if not parole:
        return []
    m = motore()
    if not m.caricato:
        return []

    insiemi = []
    for p in parole:
        insiemi.append(_versi_con(m, _prefissi(p)))
    insiemi = [s for s in insiemi if s]
    if not insiemi:
        return []

    # devono valere TUTTE le parole: prendo l'intersezione
    comuni = set.intersection(*insiemi) if len(insiemi) > 1 else insiemi[0]
    if not comuni:
        # altrimenti prendo la parola piu' rara
        comuni = min(insiemi, key=len)

    ordinati = sorted(comuni)
    gruppi: list[list[int]] = []
    for i in ordinati:
        if gruppi:
            prec = m.versetti[gruppi[-1][-1]]
            cur = m.versetti[i]
            if (cur["libro"] == prec["libro"] and cur["capitolo"] == prec["capitolo"]
                    and cur["versetto"] == prec["versetto"] + 1):
                gruppi[-1].append(i)
                continue
        gruppi.append([i])

    risultati = []
    for gruppo in gruppi:
        primo = m.versetti[gruppo[0]]
        indici_cap = m.versetti_per_capitolo.get((primo["libro"], primo["capitolo"]), [])
        try:
            pos_inizio = indici_cap.index(gruppo[0])
            pos_fine = indici_cap.index(gruppo[-1])
        except ValueError:
            pos_inizio = pos_fine = 0
        esteso = indici_cap[max(0, pos_inizio - contesto):pos_fine + contesto + 1] or gruppo
        testo_completo = "\n".join(
            f'{m.versetti[i]["riferimento"]}  {m.versetti[i]["testo"]}' for i in esteso)
        risultati.append({
            "libro": primo["libro"],
            "capitolo": primo["capitolo"],
            "riferimento_inizio": m.versetti[esteso[0]]["riferimento"],
            "riferimento_fine": m.versetti[esteso[-1]]["riferimento"],
            "riferimento": (m.versetti[esteso[0]]["riferimento"]
                            if esteso[0] == esteso[-1] else
                            f'{m.versetti[esteso[0]]["riferimento"]} - '
                            f'{m.versetti[esteso[-1]]["riferimento"]}'),
            "testo": testo_completo,
            "n_versetti": len(esteso),
            "corrispondenze": [m.versetti[i]["riferimento"] for i in gruppo],
        })

    risultati.sort(key=lambda x: (-len(x["corrispondenze"]), x["riferimento_inizio"]))
    return risultati[:max_passaggi]


def testo_capitolo(libro: str, capitolo: int) -> str:
    """Testo completo di un capitolo."""
    m = motore()
    indici = m.versetti_per_capitolo.get((libro, capitolo), [])
    return "\n".join(f'{m.versetti[i]["riferimento"]}  {m.versetti[i]["testo"]}'
                     for i in indici)
