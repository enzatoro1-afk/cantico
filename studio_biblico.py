# -*- coding: utf-8 -*-
"""
studio_biblico.py
=================
"Studio del versetto": riconosce il riferimento biblico nel testo, propone
i 4 passi dello studio induttivo (testo, contesto, significato, applicazione)
e cerca su YouTube le ESPOSIZIONI e gli STUDI BIBLICI pentecostali/ADI
(corpi di credenti, chiese evangeliche) su quel passaggio.

Le "interpretazioni" che propone l'app sono spunti di studio generati dal
testo + i video diMinistri/pastori realmente pubblicati su YouTube:
l'app non finge di essere un commentario autorevole, ma mette insieme
materiale vero e verificabile.
"""

from __future__ import annotations

import re

from text_tools import senza_accenti

# --------------------------------------------------------------------------
# Libri della Bibbia: italiano -> inglese (per query/API)
# --------------------------------------------------------------------------

LIBRI = {
    "genesi": ("Genesi", "Genesis", "Gen"),
    "esodo": ("Esodo", "Exodus", "Exod"),
    "levitico": ("Levitico", "Leviticus", "Lev"),
    "numeri": ("Numeri", "Numbers", "Num"),
    "deuteronomio": ("Deuteronomio", "Deuteronomy", "Deut"),
    "giosue": ("Giosuè", "Joshua", "Josh"),
    "giudici": ("Giudici", "Judges", "Judg"),
    "rut": ("Rut", "Ruth", "Ruth"),
    "1 samuele": ("Samuele", "1 Samuel", "1Sam"),
    "2 samuele": ("Samuele", "2 Samuel", "2Sam"),
    "1 re": ("Re", "1 Kings", "1King"),
    "2 re": ("Re", "2 Kings", "2King"),
    "1 cronache": ("Cronache", "1 Chronicles", "1Chr"),
    "2 cronache": ("Cronache", "2 Chronicles", "2Chr"),
    "esdra": ("Esdra", "Ezra", "Ezra"),
    "neemia": ("Neemia", "Nehemiah", "Neh"),
    "ester": ("Ester", "Esther", "Esth"),
    "giob": ("Giob", "Job", "Job"),
    "salmi": ("Salmi", "Psalms", "Ps"),
    "salmo": ("Salmi", "Psalms", "Ps"),
    "proverbi": ("Proverbi", "Proverbs", "Prov"),
    "ecclesiaste": ("Ecclesiaste", "Ecclesiastes", "Eccl"),
    "cantico dei cantici": ("Cantico dei Cantici", "Song of Solomon", "Song"),
    "isaia": ("Isaia", "Isaiah", "Isa"),
    "geremia": ("Geremia", "Jeremiah", "Jer"),
    "lamentazioni": ("Lamentazioni", "Lamentations", "Lam"),
    "daniele": ("Daniele", "Daniel", "Dan"),
    "osea": ("Osea", "Hosea", "Hos"),
    "gioele": ("Gioele", "Joel", "Joel"),
    "amos": ("Amos", "Amos", "Amos"),
    "giona": ("Giona", "Jonah", "Jonah"),
    "michea": ("Michea", "Micah", "Mic"),
    "sofonia": ("Sofonia", "Zephaniah", "Zeph"),
    "zaccaria": ("Zaccaria", "Zechariah", "Zech"),
    "malachia": ("Malachia", "Malachi", "Mal"),
    "matteo": ("Matteo", "Matthew", "Matt"),
    "marco": ("Marco", "Mark", "Mark"),
    "luca": ("Luca", "Luke", "Luke"),
    "giovanni": ("Giovanni", "John", "John"),
    "atti": ("Atti", "Acts", "Acts"),
    "romani": ("Romani", "Romans", "Rom"),
    "1 corinzi": ("Corinzi", "1 Corinthians", "1Cor"),
    "2 corinzi": ("Corinzi", "2 Corinthians", "2Cor"),
    "galazi": ("Galazi", "Galatians", "Gal"),
    "efesini": ("Efesini", "Ephesians", "Eph"),
    "filippesi": ("Filippesi", "Philippians", "Phil"),
    "colossesi": ("Colossesi", "Colossians", "Col"),
    "1 tessalonicesi": ("Tessalonicesi", "1 Thessalonians", "1Thess"),
    "2 tessalonicesi": ("Tessalonicesi", "2 Thessalonians", "2Thess"),
    "1 timoteo": ("Timoteo", "1 Timothy", "1Tim"),
    "2 timoteo": ("Timoteo", "2 Timothy", "2Tim"),
    "tito": ("Tito", "Titus", "Titus"),
    "filemone": ("Filemone", "Philemon", "Phlm"),
    "ebrei": ("Ebrei", "Hebrews", "Heb"),
    "giacomo": ("Giacomo", "James", "Jas"),
    "1 pietro": ("Pietro", "1 Peter", "1Pet"),
    "2 pietro": ("Pietro", "2 Peter", "2Pet"),
    "1 giovanni": ("Giovanni", "1 John", "1John"),
    "2 giovanni": ("Giovanni", "2 John", "2John"),
    "3 giovanni": ("Giovanni", "3 John", "3John"),
    "giuda": ("Giuda", "Jude", "Jude"),
    "apocalisse": ("Apocalisse", "Revelation", "Rev"),
}

# abbreviazioni comuni -> libro
ABBREVIAZIONI = {
    "gen": "genesi", "es": "esodo", "lev": "levitico", "num": "numeri",
    "deut": "deuteronomio", "gs": "giosue", "gdc": "giudici", "rt": "rut",
    "sam": "1 samuele", "re": "1 re", "cr": "1 cronache", "esd": "esdra",
    "ne": "neemia", "est": "ester", "gb": "giob", "sal": "salmi", "salmo": "salmi",
    "pr": "proverbi", "prov": "proverbi", "eccl": "ecclesiaste", "ct": "cantico dei cantici",
    "is": "isaia", "ger": "geremia", "lam": "lamentazioni", "dn": "daniele",
    "os": "osea", "jl": "gioele", "am": "amos", "gio": "giona", "mi": "michea",
    "so": "sofonia", "zc": "zaccaria", "ml": "malachia", "mt": "matteo",
    "mc": "marco", "lc": "luca", "gv": "giovanni", "at": "atti", "ro": "romani",
    "1co": "1 corinzi", "2co": "2 corinzi", "gal": "galazi", "ef": "efesini",
    "fil": "filippesi", "col": "colossesi", "1ts": "1 tessalonicesi",
    "2ts": "2 tessalonicesi", "1tm": "1 timoteo", "2tm": "2 timoteo",
    "tt": "tito", "fm": "filemone", "eb": "ebrei", "gc": "giacomo",
    "1pt": "1 pietro", "2pt": "2 pietro", "1gv": "1 giovanni", "2gv": "2 giovanni",
    "3gv": "3 giovanni", "gd": "giuda", "ap": "apocalisse",
    # abbreviazioni "collate" (il numero davanti distingue 1Cor / 2Cor ecc.)
    "cor": "corinzi", "ts": "tessalonicesi", "tm": "timoteo",
    "pi": "pietro", "ga": "galazi", "co": "colossesi",
    "ac": "atti", "de": "deuteronomio", "ge": "geremia",
}

PATTERN_RIFERIMENTO_TEMPLATO = (
    r"(?:(?P<num>\d)\s*)?"
    r"(?P<libro>{libri})"
    r"\s*\.?\s*"
    r"(?P<cap>\d{{1,3}})"
    r"(?:\s*[:,]\s*(?P<vers>\d{{1,3}}))?"
    r"(?:\s*[-–]\s*(?P<fine>\d{{1,3}}))?"
)


def _costrui_regex() -> re.Pattern:
    """Costruisce la regex con tutti i libri e le abbreviazioni."""
    # nome base -> lista di (numero, info)
    base: dict[str, list[tuple[str, tuple[str, str, str]]]] = {}

    def aggiungi(nome_chiave: str, numero: str, info: tuple[str, str, str]) -> None:
        base.setdefault(nome_chiave, []).append((numero, info))

    for chiave, info in LIBRI.items():
        parti = chiave.split()
        if parti[0].isdigit():
            aggiungi(" ".join(parti[1:]), parti[0], info)
        else:
            aggiungi(chiave, "", info)
            aggiungi(chiave, "1", info)
            aggiungi(chiave, "2", info)
            aggiungi(chiave, "3", info)

    for abbrev, chiave in ABBREVIAZIONI.items():
        if chiave in LIBRI:
            base.setdefault(abbrev, []).extend(base.get(chiave, []))
        else:
            # es. "cor" -> "corinzi" (che in LIBRI e' numerato: 1 corinzi, 2 corinzi)
            for k, info in LIBRI.items():
                parti = k.split()
                base_name = " ".join(parti[1:]) if parti[0].isdigit() else k
                if base_name == chiave:
                    numero = parti[0] if parti[0].isdigit() else ""
                    base.setdefault(abbrev, []).append((numero, info))

    nomi = sorted(base.keys(), key=len, reverse=True)
    alternativa = "|".join(re.escape(n) for n in nomi)
    pattern = PATTERN_RIFERIMENTO_TEMPLATO.format(libri=alternativa)
    return re.compile(pattern, re.IGNORECASE)


_REGEX_RIFERIMENTO = _costrui_regex()


def _normalizza_libro(parola: str) -> str | None:
    parola = parola.lower().strip()
    if parola in ABBREVIAZIONI:
        return ABBREVIAZIONI[parola]
    if parola in LIBRI:
        return parola
    return None


def rileva_riferimento(testo: str) -> dict | None:
    """
    Cerca un riferimento biblico nel testo (es. "Giovanni 3,16", "Gv 3:16",
    "1 Cor 13,4", "Sal 22,1"). Restituisce None se non trova nulla.
    """
    testo_norm = senza_accenti(testo)
    for match in _REGEX_RIFERIMENTO.finditer(testo_norm):
        nome_libro = match.group("libro").lower().strip()
        numero_libro = match.group("num") or ""
        capitolo = int(match.group("cap"))
        versetto = int(match.group("vers")) if match.group("vers") else None
        verso_fine = match.group("fine")

        # risoluzione del libro (con eventuale numero: 1 Cor, 2 Re, ...)
        scelta = None
        if nome_libro in LIBRI:
            scelta = LIBRI[nome_libro]
        elif nome_libro in ABBREVIAZIONI and ABBREVIAZIONI[nome_libro] in LIBRI:
            scelta = LIBRI[ABBREVIAZIONI[nome_libro]]
        else:
            for chiave, info in LIBRI.items():
                parti = chiave.split()
                base = " ".join(parti[1:]) if parti[0].isdigit() else chiave
                if base == nome_libro:
                    if not numero_libro:
                        scelta = info
                        break
                    if parti[0] == numero_libro:
                        scelta = info
                        break
        if not scelta:
            # fallback: nome abbreviato non in elenco ("cor" -> "corinzi")
            for chiave, info in LIBRI.items():
                parti = chiave.split()
                base = " ".join(parti[1:]) if parti[0].isdigit() else chiave
                if not (base.startswith(nome_libro) or nome_libro.startswith(base)):
                    continue
                numero = parti[0] if parti[0].isdigit() else ""
                if numero_libro and numero:
                    if numero == numero_libro:
                        scelta = info
                        break
                elif not numero_libro:
                    scelta = info
                    break
        if not scelta:
            continue

        italiano, inglese, abbrev = scelta
        rif = f"{italiano} {capitolo}"
        if versetto:
            rif += f",{versetto}"
        if verso_fine:
            rif += f"-{verso_fine}"
        return {
            "libro": italiano,
            "libro_en": inglese,
            "abbreviazione": abbrev,
            "capitolo": capitolo,
            "versetto": versetto,
            "riferimento": rif,
            "riferimento_en": f"{inglese} {capitolo}"
                              + (f":{versetto}" if versetto else ""),
        }
    return None


# --------------------------------------------------------------------------
# I 4 passi dello studio induttivo
# --------------------------------------------------------------------------

def genera_passi(testo: str, analisi: dict, riferimento: dict | None) -> list[dict]:
    """
    Costruisce i 4 passi classici dello studio del versetto, usando i temi
    rilevati nel testo.
    """
    testo = (testo or "").strip()
    temi = (analisi or {}).get("temi", [])
    tono = (analisi or {}).get("tono", "")
    salmo = (analisi or {}).get("salmo")
    rif = riferimento["riferimento"] if riferimento else "il tuo testo"

    passi = []

    # 1. IL TESTO
    passi.append({
        "titolo": "1. Il testo",
        "contenuto": (
            f"«{testo[:220]}{'...' if len(testo) > 220 else ''}»"
            + (f" ({rif})" if riferimento else "")
        ),
        "domanda": "Leggi il passaggio due volte: ad alta voce, poi lentamente. "
                   "Sottolinea le parole che ti toccano.",
    })

    # 2. IL CONTESTO
    contesto = "Leggi i versetti prima e dopo: il contesto spiega ciò che il versetto, "
    contesto += "da solo, non può spiegare."
    if riferimento:
        contesto += f" Confronta il tuo versetto con gli altri dello stesso capitolo ({rif})."
    if salmo:
        contesto += f" Attenzione alla numerazione: è {salmo['riferimento']}."
    passi.append({
        "titolo": "2. Il contesto",
        "contenuto": contesto,
        "domanda": "A chi parla Dio qui? In quale momento della sua storia? "
                   "Cosa stava succedendo intorno?",
    })

    # 3. IL SIGNIFICATO
    significato = "Chiediti che cosa Dio sta dicendo e che cosa sta chiedendo."
    if temi:
        significato += f" Nel tuo testo emergono i temi: {', '.join(temi)}."
    if tono:
        significato += f" Il tono è {tono.lower()}."
    significato += (" Non fermarti al testo: guarda cosa dice dell'identità di Dio, "
                    "della persona di Cristo e di ciò che chiede all'uomo.")
    passi.append({
        "titolo": "3. Il significato",
        "contenuto": significato,
        "domanda": "Qual è l'affermazione centrale? Qual è la promessa o il comando?",
    })

    # 4. L'APPLICAZIONE
    applicazione = "Trasforma l'ascolto in una decisione concreta per oggi."
    applicazione += " Formula una preghiera breve con la frase che ti ha colpito, "
    applicazione += "e scegli un gesto pratico (un servizio, una riconciliazione, "
    applicazione += "un'ora di lode, un'iscrizione a un gruppo)."
    passi.append({
        "titolo": "4. L'applicazione",
        "contenuto": applicazione,
        "domanda": "Cosa faccio, in concreto, nelle prossime 24 ore?",
    })

    return passi


# --------------------------------------------------------------------------
# Query per cercare le interpretazioni su YouTube
# --------------------------------------------------------------------------

def query_studio(riferimento: dict | None, testo: str = "") -> list[str]:
    """
    Query per trovare studi/esposizioni pentecostali (ADI, Assemblies of God,
    chiese evangeliche) sul passaggio indicato.
    """
    query: list[str] = []
    if riferimento:
        rif = riferimento["riferimento"]
        rif_en = riferimento["riferimento_en"]
        query.append(f"commento {rif} pentecostale")
        query.append(f"studio biblico {rif} ADI Assemblee di Dio")
        query.append(f"esposizione {rif} chiesa evangelica")
        query.append(f"{rif_en} bible study exposition")
    if testo:
        parole = [p for p in re.findall(r"[A-Za-zÀ-ÿ]{4,}", testo)][:4]
        if parole:
            frase = " ".join(parole)
            query.append(f"{frase} spiegazione bibbia pentecostale")
            query.append(f"{frase} insegnamento ADI")
    return query[:5]
