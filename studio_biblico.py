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
    r"(?:capitolo\s+|cap\.?\s*)?"
    r"(?P<cap>\d{{1,3}})"
    # "versetti dal 28 al 31" / "dal 28 al 31" / "vv. 28-31" / "28,31" / "28-31"
    r"(?:\s*(?:,|[:;]|versetti?\s*(?:dal)?|dal|vv\.?\s*(?:dal)?)\s*(?P<vers>\d{{1,3}}))?"
    r"(?:\s*(?:[-–—]|al|alla|a)\s*(?P<fine>\d{{1,3}}))?"
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
        verso_fine_num = int(verso_fine) if verso_fine else None
        if verso_fine_num:
            rif += f"-{verso_fine_num}"
        return {
            "libro": italiano,
            "libro_en": inglese,
            "abbreviazione": abbrev,
            "capitolo": capitolo,
            "versetto": versetto,
            "versetto_fine": verso_fine_num,
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


# --------------------------------------------------------------------------
# La spiegazione per iscritto: trascrizione della predicazione
# --------------------------------------------------------------------------

RUMORE_TRASCRIZIONE = re.compile(
    r"(\[[^\]]{0,40}\])|(>>+)|(\.\.\.)", re.IGNORECASE
)


def _puliscitrascrizione(frammenti: list) -> str:
    """Unisce i frammenti eliminando i marcatori di musica/applausi."""
    parti = []
    for f in frammenti:
        testo = getattr(f, "text", None)
        if testo is None:
            testo = str(f)
        testo = RUMORE_TRASCRIZIONE.sub(" ", testo)
        testo = re.sub(r"\s+", " ", testo).strip()
        if testo:
            parti.append(testo)
    return " ".join(parti)


def estrai_spiegazione(video_id: str, max_caratteri: int = 60000) -> dict | None:
    """
    Scarica la trascrizione di un video di predicazione e restituisce la
    parte parlata: è la "migliore interpretazione" scritta, presa dalla
    predicazione stessa.

    Restituisce None se il video non ha trascrizione.
    """
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except Exception:
        return None

    try:
        api = YouTubeTranscriptApi()
        try:
            frammenti = api.fetch(video_id, languages=["it", "it-IT", "en"])
        except Exception:
            try:
                frammenti = api.fetch(video_id)
            except Exception:
                return None
    except Exception:
        return None

    testo = _puliscitrascrizione(frammenti)
    if len(testo) < 120:
        return None

    # tengo la trascrizione INTEGRA (fino a un limite di sicurezza generoso)
    testo = testo[:max_caratteri]
    completo = testo.strip()

    # "intro": la parte che espone davvero (dopo eventuali intro musicali)
    intro = completo
    if len(intro) > 900:
        punto = intro.rfind(". ", 500, 900)
        if punto > 0:
            intro = intro[:punto + 1]

    return {
        "video_id": video_id,
        "testo": completo,        # testo integrale della predicazione
        "intro": intro,            # parte iniziale leggibile
        "caratteri": len(completo),
        "parole": len(completo.split()),
    }


# --------------------------------------------------------------------------
# FASE 1: interpretazione dottrinale pentecostale + parole chiave spirituali
# --------------------------------------------------------------------------

PROMPT_INTERPRETAZIONE = """Sei un assistente biblico di dottrina Cristiana Evangelica Pentecostale (linea ADI / Assemblee di Dio).
Prendi il seguente riferimento: {riferimento}
{testo_versetto}Estrai il testo intero se e' presente solo il capitolo.
Fornisci una breve interpretazione teologica focalizzata sui temi della lode, della fede, del ravvedimento o della consolazione spirituale.
Infine, estrai le 3 parole chiave spirituali piu' forti (es. 'Fortezza', 'Salvezza', 'Fedelta') derivate da questa interpretazione."""

# lessico spirituale pesato: dal piu' forte al piu' generico
LESSICO_SPIRITUALE = (
    ("redenzione", 10), ("salvezza", 10), ("consolazione", 9), ("fortezza", 9),
    ("rifugio", 9), ("scudo", 9), ("speranza", 8), ("fedeltà", 8),
    ("fedele", 8), ("misericordia", 8), ("perdono", 8), ("ravvedimento", 8),
    ("pentecoste", 8), ("spiritualità", 7), ("santificazione", 7),
    ("confessione", 7), ("obbedienza", 7), ("coraggio", 7), ("protezione", 7),
    ("sostegno", 7), ("fiducia", 7), ("resurrezione", 7), ("risurrezione", 7),
    ("vita", 6), ("luce", 6), ("verità", 6), ("grazia", 6), ("amore", 6),
    ("lode", 6), ("adorazione", 6), ("preghiera", 6), ("pastore", 6),
    ("salvatore", 6), ("sacrificio", 6), ("croce", 6), ("pazienza", 5),
    ("umiltà", 5), ("povertà", 5), ("zelo", 5), ("missione", 5),
    ("testimonianza", 5), ("fratellanza", 5),
    ("comandamento", 7), ("comandamenti", 7), ("prossimo", 7), ("cuore", 6),
    ("anima", 5), ("mente", 5), ("forza", 5), ("giustizia", 6), ("regno", 6),
    ("alleanza", 6), ("patto", 5), ("eredità", 5), ("vocazione", 6),
    ("chiamata", 5), ("annuncio", 6), ("vangelo", 6), ("tempio", 5),
    ("pane", 5), ("vino", 5), ("mensa", 5), ("sangue", 5), ("ascensione", 6),
    ("liberazione", 7), ("riscatto", 7), ("espiazione", 7), ("propiziazione", 6),
    ("intercessione", 7), ("mediatore", 7), ("avvocato", 6), ("passione", 6),
    ("ministero", 6), ("ufficio", 5), ("cenacolo", 6), ("doni", 5),
    ("parola", 5), ("verbo", 5), ("confessione", 7), ("lode", 6),
)


def estrai_parole_chiave_spirituali(testo: str, numero: int = 3) -> list[str]:
    """
    Dall'interpretazione teologica estrae le N parole chiave spirituali piu'
    forti. Usa un lessico pesato; se non trova niente, prende le parole
    significative piu' frequenti.
    """
    testo_norm = senza_accenti(testo or "")
    punteggi: dict[str, float] = {}

    for parola, peso in LESSICO_SPIRITUALE:
        if parola in testo_norm:
            punteggi[parola] = punteggi.get(parola, 0.0) + peso

    if not punteggi:
        # fallback prudente: solo parole "solide" (>= 6 lettere, non generiche)
        parole = [p for p in re.findall(r"[a-z]{6,}", testo_norm)
                  if p not in ("signore", "questo", "questa", "nostro", "vostro",
                               "fratello", "sorella", "presente", "passato",
                               "davvero", "perche", "quando", "mentre", "adesso",
                               "stesso", "altro", "giorno", "sempre", "ancora",
                               "insieme", "attorno", "quando", "stato")]
        conteggio: dict[str, int] = {}
        for p in parole:
            conteggio[p] = conteggio.get(p, 0) + 1
        ordinati = sorted(conteggio.items(), key=lambda kv: -kv[1])
        return [p for p, _ in ordinati[:numero]]

    ordinati = sorted(punteggi.items(), key=lambda kv: (-kv[1], kv[0]))
    return [p for p, _ in ordinati[:numero]]


def interpretazione_dotrinale(versetto: dict | None, tema: str = "",
                              parole_chiave: list[str] | None = None) -> dict:
    """
    Genera una breve interpretazione teologica di dottrina evangelica
    pentecostale. Usa, in ordine di preferenza:
      1. la trascrizione di una predica/esposizione reale trovata su YouTube;
      2. il motore tematico dell'app (interpretazione di studio).
    """
    parole_chiave = parole_chiave or []
    if versetto:
        # se e' un passaggio o un capitolo, uso TUTTO il testo
        testo_versetto = (versetto.get("testo_passaggio")
                          or versetto.get("testo_capitolo")
                          or versetto.get("testo_pulito")
                          or versetto.get("testo", ""))
        riferimento = versetto.get("riferimento", "")
    else:
        testo_versetto = ""
        riferimento = ""

    # 1) interpretazione reale dalla predicazione (se disponibile)
    if versetto and versetto.get("trascrizione"):
        testo = versetto["trascrizione"]
        return {
            "testo": testo,
            "parole_chiave": estrai_parole_chiave_spirituali(testo),
            "fonte": "predicazione (trascrizione reale)",
            "riferimento": riferimento,
        }

    # 2) interpretazione di studio COMPLETA, strutturata come uno studio biblico
    tema = tema or "Salvezza"
    frasi_tema = {
        "Consolazione": "Per la CONSOLAZIONE: e' un invito a poggiare su Dio nei "
                        "momenti di prova, perche' Egli non abbandona il suo popolo. "
                        "Nella lode si canta questo perche' Dio e' la nostra "
                        "speranza quando la terra trema.",
        "Proclamazione": "Per la LODE: questo passaggio viene cantato per esaltare "
                         "Dio e chiamare l'assemblea all'adorazione. E' un "
                         "inno di vittoria, non un'inno di circostanza.",
        "Salvezza": "Per la SALVEZZA: annuncia la grazia di Dio e chiama alla "
                    "conversione, perche' solo in Cristo c'e' salvezza.",
        "Amore": "Per l'AMORE: mostra l'amore che Dio porta a ciascuno dei suoi "
                 "figli, anche quando falliscono: e' un amore che non si "
                 "ritira.",
        "Fede": "Per la FEDE: e' un invito a credere e a fidarsi di Dio anche "
                "quando non si capisce il percorso.",
        "Preghiera": "Per la PREGHIERA: e' un invito a pregare e a cercare Dio "
                     "in ogni momento, come gli apostoli che gli chiesero: "
                     "'Signore, insegnaci a pregare'.",
        "Coraggio": "Per il CORAGGIO: e' un invito a non temere e ad affrontare "
                    "le prove con fortezza, sapendo che Dio cammina con noi.",
        "Guarigione": "Per la GUARIGIONE: annuncia la guarigione che viene da "
                      "Dio, del corpo e dello spirito.",
        "Speranza": "Per la SPERANZA: e' l'invito a non perdere la fiducia in "
                    "Dio, perche' le sue promesse sono certe.",
        "Umiltà": "Per l'UMILTA': richiama all'umiltà e al servizio, come Gesù "
                  "che si è fatto servo.",
        "Paternità": "Per la PATERNITA': ricorda il cuore di Dio come Padre, che "
                     "prende cura dei suoi figli.",
        "Servizio": "Per il SERVIZIO: chiama a servire e a portare il messaggio "
                    "a chi non lo conosce.",
        "Battesimo": "Per il BATTESIMO: parla del nuovo inizio in Cristo, che "
                     "si riceve per fede e si vive in santita'.",
    }
    frase = frasi_tema.get(tema, frasi_tema["Salvezza"])
    nucleo = ", ".join(parole_chiave[:3]) if parole_chiave else "la fiducia in Dio"

    # contesto reale (versetti vicini), se disponibili
    contesto_txt = ""
    if isinstance(versetto, dict):
        _vicini = (versetto.get("contesto_prima", []) +
                   versetto.get("contesto_dopo", []))
        if _vicini:
            contesto_txt = ("\n\n".join(
                f'{c["riferimento"]}  {c["testo"]}' for c in _vicini[:3]))
    if not contesto_txt:
        contesto_txt = ("Leggi i versetti che precedono e seguono: il testo non "
                        "si capisce da solo, perche' nasce dentro una "
                        "conversazione viva con il popolo di Dio.")

    corpo = (
        f"{riferimento}\n"
        f"{'=' * (len(riferimento) + 2)}\n\n"

        f"1. IL TESTO\n"
        f"{'-' * 9}\n"
        f"{testo_versetto}\n\n"

        f"2. IL CONTESTO (i versetti vicini)\n"
        f"{'-' * 37}\n"
        f"{contesto_txt}\n\n"

        f"3. IL SIGNIFICATO (dottrina evangelica pentecostale)\n"
        f"{'-' * 50}\n"
        f"Questo passo parla di {tema.lower()}. Il punto centrale, nella "
        f"dottrina evangelica pentecostale, e' questo: Dio agisce per primo e "
        f"l'uomo risponde con fede. Non e' l'uomo a muoversi per primo, e' Dio "
        f"che prende l'iniziativa; la nostra risposta e' la fede, cioe' "
        f"affidarsi a Lui con tutto il cuore.\n\n"
        f"Il nucleo spirituale di questo testo sta in {nucleo}. "
        f"Leggendo il passaggio con questa lente, si capisce perche' la "
        f"Chiesa lo ha sempre cantato e predicato: non come uno spettacolo, ma "
        f"come la dichiarazione di una fiducia che regge anche nella notte.\n\n"

        f"4. L'APPLICAZIONE (le 4 domande dello studio induttivo)\n"
        f"{'-' * 47}\n"
        f"- Che cosa dice il testo? Chi parla, a chi, e che cosa afferma?\n"
        f"- Che cosa significa per me, qui e adesso? Cosa mi chiede di credere?\n"
        f"- Che cosa devo smettere di fare e che cosa devo cominciare a fare?\n"
        f"- Chi devo ringraziare e a chi devo portare questa parola?\n\n"

        f"5. PER LA LODE, IL RAVVEDIMENTO E LA CONSOLAZIONE\n"
        f"{'-' * 44}\n"
        f"{frase}\n\n"

        f"LE 3 PAROLE CHIAVE SPIRITUALI DI QUESTO PASSAGGIO\n"
        f"{'-' * 47}\n"
        f"{nucleo}\n"
    )

    return {
        "testo": corpo,
        "parole_chiave": (estrai_parole_chiave_spirituali(testo_versetto)[:3]
                           or estrai_parole_chiave_spirituali(corpo)[:3]
                           or parole_chiave[:3]),
        "fonte": "studio (dottrina evangelica pentecostale)",
        "riferimento": riferimento,
    }

