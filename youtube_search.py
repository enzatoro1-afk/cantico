# -*- coding: utf-8 -*-
"""
youtube_search.py
=================
Motore di ricerca dell'app "Assistente Canzoni Pentecostali per TikTok".

Non usa ALCUNA API a pagamento: interroga direttamente la pagina di ricerca
pubblica di YouTube, ne estrae il blocco di dati JSON (`ytInitialData`) e ne
legge i risultati (titolo, canale, durata, link).

Contiene:
  - estrazione delle parole chiave da un testo biblico/riflessione (IT + EN)
  - costruzione automatica della query di ricerca
  - scraping dei risultati YouTube
  - ordinamento per rilevanza rispetto al testo inserito
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Iterable
from urllib.parse import quote_plus

try:  # 'requests' è dichiarato in requirements.txt, ma restiamo robusti
    import requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore


# --------------------------------------------------------------------------
# Configurazione
# --------------------------------------------------------------------------

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# Filtro YouTube "solo video" (esclude canali e playlist dalla ricerca)
FILTRO_SOLO_VIDEO = "EgIQAQ%3D%3D"

TIMEOUT = 20

# --------------------------------------------------------------------------
# Lessico: parole da scartare e parole "religioushe" da privilegiare
# --------------------------------------------------------------------------

STOPWORDS = {
    # italiano
    "a", "ad", "al", "alla", "alle", "allo", "ai", "gli", "loro", "io", "tu",
    "egli", "ella", "noi", "voi", "loro", "mi", "ti", "ci", "vi", "si", "ne",
    "ma", "ed", "che", "chi", "cui", "non", "piu", "per", "perche", "perché",
    "come", "con", "senza", "tra", "fra", "del", "dello", "della", "dei",
    "degli", "delle", "dal", "dalla", "dei", "delle", "su", "sul", "sulla",
    "nel", "nella", "nei", "nelle", "sul", "sulla", "suo", "sua", "suoi",
    "sue", "mio", "mia", "miei", "mie", "tuo", "tua", "tuoi", "tue", "nostro",
    "nostra", "vostro", "vostra", "questo", "questa", "questi", "queste",
    "quello", "quella", "quelli", "quelle", "cio", "cui", "che", "dove",
    "quando", "come", "se", "oppure", "ancora", "gia", "già", "solo",
    "sono", "sei", "e", "stato", "essere", "hanno", "ha", "ho", "abbiamo",
    "avrà", "avro", "avro", "faccio", "fare", "fa", "fanno", "sono", "stai",
    "stiamo", "voglio", "vuoi", "possiamo", "deve", "devo", "dobbiamo",
    "questo", "questa", "citta", "città", "casa", "mondo", "vita", "giorni",
    "giorno", "tempo", "ora", "oggi", "ieri", "domani", "sempre", "mai",
    "poi", "infine", "anzi", "tuttavia", "percio", "perciò", "poiche",
    "poiché", "mentre", "finche", "finché", "dopo", "prima", "dentro",
    "fuori", "sopra", "sotto", "verso", "contro", "attraverso", "ogni",
    "tutto", "tutti", "tutte", "altro", "altra", "altri", "altre", "quello",
    "quando", "cosa", "cose", "modo", "maniera", "luogo", "parte", "punto",
    "sempre", "mai", "molto", "poco", "troppo", "meno", "anche", "ancora",
    "ora", "adesso", "allora", "quindi", "percio", "infatti", "ecco",
    # inglese (versi biblici tradotti o testi misti)
    "the", "and", "for", "you", "your", "our", "his", "her", "their", "with",
    "that", "this", "these", "those", "will", "shall", "not", "but", "all",
    "are", "was", "were", "be", "been", "being", "has", "have", "had", "did",
    "does", "do", "can", "could", "would", "should", "may", "might", "must",
    "when", "where", "which", "who", "whom", "what", "how", "why", "if",
    "because", "so", "than", "then", "there", "here", "he", "she", "it",
    "we", "they", "as", "by", "from", "up", "down", "out", "off", "over",
    "into", "about", "on", "in", "at", "to", "of", "is", "am", "in", "let",
    "unto", "unto", "even", "also", "much", "many", "more", "most", "some",
    "such", "only", "own", "same", "too", "very", "s", "t", "don", "now",
}

# Parole tipiche del tema religioso: se presenti nel testo, sono ottime
# parole chiave di ricerca (pesano di più).
TERMINE_RELIGIOSI = {
    "dio", "dea", "signore", "gesu", "gesù", "cristo", "cristiano", "cristiana",
    "cristiani", "spirito", "santo", "santa", "santissimo", "trinità", "trinità",
    "padre", "figlio", "madre", "madonna", "maria", "gesus", "maria",
    "amore", "fede", "grazia", "verita", "verità", "salvezza", "salvatore",
    "perdono", "redenzione", "risurrezione", "resurrezione", "croce", "calice",
    "preghiera", "lode", "lodi", "adorazione", "adora", "innocente", "peccato",
    "peccati", "confessione", "battesimo", "comunione", "eucaristia",
    "anima", "cuore", "pace", "speranza", "gioia", "lacrime", "sofferenza",
    "croce", "resurrezione", "alleanza", "testamento", "parabola", "miracolo",
    "vangelo", "bibbia", "scrittura", "salmo", "proverbi", "apocalisse",
    "chiesa", "pastore", "predica", "testimone", "testimonianza", "servire",
    "servizio", "umilta", "umiltà", "santificazione", "trasformazione",
    "ministero", "avvento", "pentecoste", "quaresima", "pasqua", "resurrezione",
}

# Suffissi che accrescono l'attinenza al genere "musica evangelica"
SUFFISSI_GENRE = (
    "pentecostale", "pentecostal", "pentecostali", "evangelica", "evangelico",
    "evangelici", "lode", "lodi", "inno", "inni", "canto", "canti", "coro",
    "adorazione", "worship", "cristiana", "cristiano", "christian", "spiritual",
    "hymn", "salmo", "biblico",
)


# --------------------------------------------------------------------------
# Filtro di confessione: l'app serve contenuti EVANGELICI / PENTECOSTALI.
# I contenuti cattolici (liturgia, santuari, mariani, catechismo) vengono
# scartati; quelli pentecostali/evangelici vengono privilegiati.
# --------------------------------------------------------------------------

TERMINI_CATTOLICI = (
    "cattolic", "cattolico", "cattolica", "cattolici", "vaticano", "vatican",
    "papa ", "parrocchia", "liturgia", "mariano", "mariana", "madonna",
    "santuario", "monaci", "monastero", "suore", "indulgenza", "rosario",
    "catechismo", "dottrina della chiesa", "viatico", "canonizz", "beatific",
    "chiesa di roma", "chiesa ortodossa", "chiesa copta", "chiesa cattolica",
    "vespro", "lauretana", "ave maria", "salve regina", "vescovo", "diocesi",
    "chiesa madre", "santuari", "madre church",
)

TERMINI_EVANGELICI = (
    "pentecostal", "pentecostale", "pentecostali", "chiesa evangelica",
    "evangelica", "evangelico", "evangelici", "assemblee di dio", "adorazione",
    "culto", "veglia di preghiera", "vocal", "coro", "inno", "worship",
    "praise", "christian", "cristiana", "cristiano", "cristianesimo",
    "battesimo", "evangelizzazione", "biblica", "biblia",
)


def punteggio_confessione(titolo: str, canale: str) -> float:
    """
    + se il contenuto e' evangelico/pentecostale, - se e' cattolico.
    """
    t = ((titolo or "") + " " + (canale or "")).lower()
    punteggio = 0.0
    for termine in TERMINI_EVANGELICI:
        if termine in t:
            punteggio += 2.0
            break
    for termine in TERMINI_CATTOLICI:
        if termine in t:
            punteggio -= 12.0
            break
    return punteggio


def è_cattolico(titolo: str, canale: str) -> bool:
    """True se il contenuto è apertamente cattolico (va escluso)."""
    t = ((titolo or "") + " " + (canale or "")).lower()
    return any(termine in t for termine in TERMINI_CATTOLICI)


# --------------------------------------------------------------------------
# Modello dati
# --------------------------------------------------------------------------

@dataclass
class Risultato:
    """Un video di YouTube candidato a 'canzone'."""

    titolo: str
    video_id: str
    canale: str = ""
    durata: str = ""
    secondi: int | None = None
    punteggio: float = 0.0
    visualizzazioni: int = 0

    @property
    def url(self) -> str:
        return f"https://www.youtube.com/watch?v={self.video_id}"

    @property
    def url_miniature(self) -> str:
        return f"https://i.ytimg.com/vi/{self.video_id}/hqdefault.jpg"

    @property
    def url_tiktok(self) -> str:
        return f"https://www.tiktok.com/search?q={quote_plus(self.titolo)}"


class ErroreRicerca(Exception):
    """Errore leggibile da mostrare all'utente."""


# --------------------------------------------------------------------------
# 1) Estrazione parole chiave dal testo
# --------------------------------------------------------------------------

def _normalizza(testo: str) -> list[str]:
    """Minuscole, senza accenti, solo sequenze alfabetiche."""
    testo = testo.lower()
    # toglie accenti: à -> a, è -> e, ù -> u ...
    testo = "".join(c for c in unicodedata_normalize(testo) if True)
    return re.findall(r"[a-zà-ÿ']+", testo)


def unicodedata_normalize(testo: str) -> str:
    """Versione minima di unicodedata.normalize (NFKD) senza dipendenze."""
    import unicodedata

    return unicodedata.normalize("NFKD", testo)


def estrai_parole_chiave(testo: str, max_parole: int = 3) -> list[str]:
    """
    Estrae le parole chiave più significative da un versetto/riflessione.

    Regole:
      - scarta le stopword (italiano/inglese)
      - scarte parole troppo corte (1-2 lettere)
      - le parole del lessico religioso hanno peso maggiore
      - in caso di parità, l'ordine di comparsia nel testo viene preservato
    """
    if not testo or not testo.strip():
        return []

    tokens = _normalizza(testo)
    conteggio: dict[str, float] = {}
    ordine: dict[str, int] = {}

    for pos, token in enumerate(tokens):
        parola = token.strip("'")
        if len(parola) < 3:
            continue
        if parola in STOPWORDS:
            continue
        peso = 1.0
        if parola in TERMINE_RELIGIOSI:
            peso += 2.0
        if parola in ("signore", "dio", "gesu", "gesù", "amore", "fede"):
            peso += 0.5
        conteggio[parola] = conteggio.get(parola, 0.0) + peso
        ordine.setdefault(parola, pos)

    if not conteggio:
        # Testo fatto solo di stopword: usa le parole più lunghe trovate
        fallback = [t for t in dict.fromkeys(tokens) if len(t) >= 3][:max_parole]
        return fallback

    ordinamento = sorted(
        conteggio.items(),
        key=lambda kv: (-kv[1], ordine[kv[0]]),
    )

    risultati: list[str] = []
    for parola, _ in ordinamento:
        if any(parola in gia or gia in parola for gia in risultati):
            continue  # evita parole redundanti ("amore" / "amorevole")
        risultati.append(parola)
        if len(risultati) >= max_parole:
            break
    return risultati


# --------------------------------------------------------------------------
# 2) Costruzione della query YouTube
# --------------------------------------------------------------------------

STILI: dict[str, list[str]] = {
    "Lodi pentecostali / ADI": [
        "inno pentecostale",
        "canto di lode ADI",
    ],
    "Inni evangelici tradizionali": [
        "inno evangelico tradizionale",
        "coro evangelico lode",
    ],
    "Canzoni cristiane moderne": [
        "canzone cristiana worship",
        "musica cristiana lode moderna",
    ],
    "Mix (tutte le proposte)": [
        "inno pentecostale",
        "inno evangelico",
        "canto di lode ADI",
    ],
}

# Filtro fisso: va SEMPRE aggiunto alle parole chiave
FILTRO_PENTECOSTALE = ("musica cristiana evangelica pentecostale "
                       "lodi ADI cantico evangelico")

# Keyword negative: il "-" di YouTube esclude i risultati non pertinenti
# (canzoni mondane, liturgia/cantici cattolici, cori gregoriani, remix...)
KEYWORD_NEGATIVE = ("-cattolica -cattolico -messa -mondana -pop -remix "
                     "-gregoriano -mariano")

# Riconosce "Salmo 23", "Salmi 91", "Psalm 23"
RE_SALMO = re.compile(r"\b(?:salmi?|salmos?|psalms?)\s*\.?\s*(\d{1,3})", re.IGNORECASE)

# Riconosce "Giovanni 3", "1 Corinzi 13", "Proverbi 3"
RE_LIBRO_CAPITOLO = re.compile(
    r"\b(?:[1-3]\s+)?([A-Za-z\u00c0-\u00ff]{3,14})\s*\.?\s+(\d{1,3})"
    r"(?:\s*[:,]\s*\d{1,3})?", re.IGNORECASE
)


def _riferimento_prioritario(testo: str) -> str | None:
    """
    Se il testo contiene un libro+capitolo (es. "Salmo 23", "Giovanni 3"),
    restituisce la stringa da mettere in TESTA alla query, cosi' la ricerca
    si concentra sulla lode di quel capitolo preciso.
    """
    testo = testo or ""
    m = RE_SALMO.search(testo)
    if m:
        return f"Salmo {m.group(1)}"

    try:
        from studio_biblico import LIBRI
    except Exception:
        return None

    for m2 in RE_LIBRO_CAPITOLO.finditer(testo):
        nome = m2.group(1).strip().lower()
        for chiave, (italiano, _ing, _ab) in LIBRI.items():
            parti = chiave.split()
            base = " ".join(parti[1:]) if parti[0].isdigit() else chiave
            if nome in (base, chiave):
                numero_libro = parti[0] if parti[0].isdigit() else ""
                etichetta = f"{numero_libro} {italiano}" if numero_libro else italiano
                return f"{etichetta} {m2.group(2)}"
    return None


def costruisci_query(testo: str, stile: str = "Lodi pentecostali / ADI",
                     extra: str = "", max_parole: int = 5) -> list[str]:
    """
    Compone la query finale: [parole chiave] + [filtro pentecostale fisso]
    + [variante di stile] + [parole negative].

    Esempio:
        "Il Signore e il mio pastore"
        -> "signore pastore musica cristiana evangelica pentecostale lodi ADI
            cantico evangelico inno pentecostale -cattolica -messa -pop"

    Se il testo contiene un Salmo o un libro+capitolo, la prima query parte
    da quel riferimento ("Salmo 23 ...") per puntare alla lode precisa.
    """
    # pulisco il versetto da eventuali note/strumenti delle Bibbie online
    try:
        from text_tools import pulisci_versetto, rileva_mood
        testo = pulisci_versetto(testo)
        mood = rileva_mood(testo)
    except Exception:
        mood = None

    parole = estrai_parole_chiave(testo, max_parole=max_parole)
    varianti = STILI.get(stile, STILI["Lodi pentecostali / ADI"])
    query: list[str] = []

    def _aggiungi(q: str) -> None:
        q = " ".join(q.split()).strip()
        if q and q not in query:
            query.append(q)

    # 1) PRIORITA' al capitolo/Salmo indicato
    riferimento = _riferimento_prioritario(testo)
    if riferimento:
        _aggiungi(f"{riferimento} {FILTRO_PENTECOSTALE} {KEYWORD_NEGATIVE}")

    # 2) parole chiave + filtro fisso + variante di stile + mood + esclusioni
    base = " ".join(parole)
    mood_words = " ".join(mood["parole"]) if mood else ""
    for variante in varianti:
        _aggiungi(f"{base} {FILTRO_PENTECOSTALE} {variante} {mood_words} "
                  f"{KEYWORD_NEGATIVE}".strip())

    # 3) se il testo e' breve, query col testo integrale (piu' precisa)
    if testo and len(testo) <= 110:
        _aggiungi(f"{testo} {FILTRO_PENTECOSTALE} {KEYWORD_NEGATIVE}")

    if extra:
        query = [f"{q} {extra}".strip() for q in query]
    return query[:4]


# --------------------------------------------------------------------------
# 3) Scraping di YouTube
# --------------------------------------------------------------------------

def _estrai_ytinitialdata(html: str) -> dict | None:
    """
    Estrae e decodifica il blocco JSON `ytInitialData` dalla pagina HTML.
    Usa un bilanciatore di graffe per trovare la fine esatta del JSON.
    """
    marcatori = (
        "var ytInitialData = ",
        'ytInitialData" = ',
        'window["ytInitialData"] = ',
        "window['ytInitialData'] = ",
        "ytInitialData = ",
    )
    for marcatore in marcatori:
        idx = html.find(marcatore)
        if idx == -1:
            continue
        start = html.find("{", idx)
        if start == -1:
            continue
        profondita = 0
        in_stringa = False
        escape = False
        for i in range(start, len(html)):
            c = html[i]
            if in_stringa:
                if escape:
                    escape = False
                elif c == "\\":
                    escape = True
                elif c == '"':
                    in_stringa = False
                continue
            if c == '"':
                in_stringa = True
            elif c == "{":
                profondita += 1
            elif c == "}":
                profondita -= 1
                if profondita == 0:
                    try:
                        return json.loads(html[start:i + 1])
                    except json.JSONDecodeError:
                        return None
    return None


def _walk(obj: Any, chiave: str, raccolta: list) -> None:
    """Cerca ricorsivamente tutti gli oggetti con una data chiave."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == chiave and isinstance(v, dict):
                raccolta.append(v)
            else:
                _walk(v, chiave, raccolta)
    elif isinstance(obj, list):
        for item in obj:
            _walk(item, chiave, raccolta)


def _testo(node: Any) -> str:
    """Legge {'runs':[{'text':...}]} oppure {'simpleText':...}."""
    if not isinstance(node, dict):
        return ""
    if "simpleText" in node:
        return node.get("simpleText", "")
    runs = node.get("runs")
    if isinstance(runs, list):
        return "".join(r.get("text", "") for r in runs if isinstance(r, dict))
    if "text" in node and isinstance(node["text"], str):
        return node["text"]
    return ""


def _numero_italiano(testo: str) -> int:
    """'1.234 visualizzazioni' -> 1234 ; '1,2 M' -> 1200000"""
    testo = (testo or "").lower().replace("\u00a0", " ")
    numero = ""
    for ch in testo:
        if ch.isdigit():
            numero += ch
        elif ch in ".," and numero and len(numero) < 9:
            continue
        else:
            break
    if not numero:
        return 0
    try:
        n = int(numero.replace(".", "").replace(",", ""))
    except ValueError:
        return 0
    if " m" in testo or " mln" in testo:
        n *= 1000000
    elif " k" in testo:
        n *= 1000
    return n


def _durata_secondi(testo_durata: str) -> int | None:
    """'5:16' -> 316 | '1:18:35' -> 4715 | 'LIVE' -> None"""
    testo_durata = (testo_durata or "").strip()
    if ":" not in testo_durata:
        return None
    try:
        parti = [int(p) for p in testo_durata.split(":")]
    except ValueError:
        return None
    secondi = 0
    for p in parti:
        secondi = secondi * 60 + p
    return secondi


def _punteggio_video(titolo: str, canale: str, secondi: int | None,
                     parole_chiave: Iterable[str]) -> float:
    """Stima quanto un video è adatto come 'canzone' per il testo inserito."""
    # normalizzo i separatori: "Giovanni 14:6" == "Giovanni 14,6"
    t = (titolo or "").lower().replace(":", ",").replace(".", ",")
    c = (canale or "").lower()
    punteggio = 0.0

    for kw in parole_chiave:
        kw = kw.lower()
        if kw in t:
            punteggio += 4.0
        if kw in c:
            punteggio += 1.0

    for s in SUFFISSI_GENRE:
        if s in t:
            punteggio += 1.5
        if s in c:
            punteggio += 1.0

    # confessione: privilegia evangelico/pentecostale, penalizza cattolico
    punteggio += punteggio_confessione(titolo, canale)

    if secondi is not None:
        if 180 <= secondi <= 330:      # 3:00 - 5:30 -> il brano singolo ideale
            punteggio += 2.5
        elif 100 <= secondi <= 900:    # 1:40 - 15:00 -> durata tipica di un inno
            punteggio += 2.0
        elif secondi < 75:              # spezzoni/intro troppo corti
            punteggio -= 3.0
        elif secondi > 3600:            # compilation lunghe
            punteggio -= 1.5

    if "- topic" in c:                  # audio ufficiale: utile ma meno "canzone"
        punteggio -= 0.5

    return punteggio


def cerca_youtube(query: str, max_risultati: int = 5,
                  parole_chiave: Iterable[str] = (),
                  max_durata: int | None = None,
                  min_durata: int | None = None) -> list[Risultato]:
    """
    Esegue una ricerca su YouTube e restituisce i risultati ordinati per
    rilevanza. Non richiede API key.
    """
    if requests is None:  # pragma: no cover
        raise ErroreRicerca(
            "Il pacchetto 'requests' non è installato. Aggiungilo con: pip install requests"
        )

    try:
        risposta = requests.get(
            "https://www.youtube.com/results",
            # hl=it / gl=IT: forza la ricerca in italiano e sull'area Italia
            params={"search_query": query, "sp": FILTRO_SOLO_VIDEO,
                    "hl": "it", "gl": "IT"},
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        risposta.raise_for_status()
    except requests.exceptions.RequestException as exc:
        # piano B: yt-dlp (se installato) oppure messaggio d'errore
        alternativi = _cerca_con_ytdlp(query, max_risultati, max_durata)
        if alternativi:
            return alternativi
        raise ErroreRicerca(
            "Non sono riuscito a raggiungere YouTube. Controlla la connessione e riprova."
        ) from exc

    # YouTube risponde in UTF-8: forziamo la decodifica corretta
    risposta.encoding = "utf-8"
    html = risposta.text

    dati = _estrai_ytinitialdata(html)
    if dati is None:
        alternativi = _cerca_con_ytdlp(query, max_risultati, max_durata)
        if alternativi:
            return alternativi
        raise ErroreRicerca(
            "YouTube ha risposto con un formato inatteso. Riprova tra qualche minuto."
        )

    video_renderers: list[dict] = []
    _walk(dati, "videoRenderer", video_renderers)

    risultati: list[Risultato] = []
    visti: set[str] = set()

    for v in video_renderers:
        video_id = v.get("videoId", "")
        if not video_id or video_id in visti:
            continue
        titolo = _testo(v.get("title"))
        if not titolo:
            continue
        canale = _testo(v.get("ownerText"))
        # scarto i contenuti cattolici: qui vanno solo evangelici/pentecostali
        if è_cattolico(titolo, canale):
            continue
        durata = _testo(v.get("lengthText"))
        secondi = _durata_secondi(durata)
        visualizzazioni = _numero_italiano(_testo(v.get("viewCountText")))
        # scarto i video troppo lunghi (compilazioni, culti registrati)
        if max_durata is not None and secondi is not None and secondi > max_durata:
            continue
        if min_durata is not None and secondi is not None and secondi < min_durata:
            continue
        visti.add(video_id)
        risultati.append(
            Risultato(
                titolo=titolo.strip(),
                video_id=video_id,
                canale=canale.strip(),
                durata=durata.strip(),
                secondi=_durata_secondi(durata),
                visualizzazioni=visualizzazioni,
            )
        )

    if not risultati:
        alternativi = _cerca_con_ytdlp(query, max_risultati, max_durata)
        if alternativi:
            return alternativi

    # FALLBACK: query troppo restrittiva (troppe parole chiave/negative)?
    # riprovo senza le keyword negative: il filtro cattolico resta attivo
    # lato Python, quindi il risultato resta evangelico.
    if not risultati and "-" in query:
        query_meno_negativi = " ".join(
            w for w in query.split() if not w.startswith("-"))
        if query_meno_negativi != query:
            try:
                risposta2 = requests.get(
                    "https://www.youtube.com/results",
                    params={"search_query": query_meno_negativi,
                            "sp": FILTRO_SOLO_VIDEO, "hl": "it", "gl": "IT"},
                    headers=HEADERS, timeout=TIMEOUT)
                risposta2.raise_for_status()
                risposta2.encoding = "utf-8"
                dati2 = _estrai_ytinitialdata(risposta2.text)
                if dati2 is not None:
                    render2: list[dict] = []
                    _walk(dati2, "videoRenderer", render2)
                    visti2: set[str] = set()
                    for v in render2:
                        vid = v.get("videoId", "")
                        if not vid or vid in visti2:
                            continue
                        titolo2 = _testo(v.get("title"))
                        if not titolo2:
                            continue
                        canale2 = _testo(v.get("ownerText"))
                        if è_cattolico(titolo2, canale2):
                            continue
                        durata2 = _testo(v.get("lengthText"))
                        sec2 = _durata_secondi(durata2)
                        if max_durata is not None and sec2 is not None \
                                and sec2 > max_durata:
                            continue
                        visti2.add(vid)
                        risultati.append(Risultato(
                            titolo=titolo2.strip(), video_id=vid,
                            canale=canale2.strip(), durata=durata2.strip(),
                            secondi=sec2))
            except Exception:
                pass

    return ordina_per_rilevanza(risultati, parole_chiave)[:max_risultati]


def _cerca_con_ytdlp(query: str, max_risultati: int,
                     max_durata: int | None = None) -> list[Risultato]:
    """Piano di riserva opzionale: usa yt-dlp se è installato."""
    try:
        from yt_dlp import YoutubeDL  # type: ignore
    except Exception:
        return []

    try:
        opzioni = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "skip_download": True,
            "socket_timeout": TIMEOUT,
        }
        with YoutubeDL(opzioni) as ydl:
            info = ydl.extract_info(f"ytsearch{max_risultati}:{query}", download=False)
        entries = (info or {}).get("entries") or []
        risultati = []
        for e in entries:
            if not e:
                continue
            durata = e.get("duration")
            secondi = int(durata) if isinstance(durata, (int, float)) else None
            # rispetto il filtro durata anche nel metodo di riserva
            if max_durata is not None and secondi is not None and secondi > max_durata:
                continue
            if secondi is None:
                continue
            risultati.append(
                Risultato(
                    titolo=(e.get("title") or "").strip(),
                    video_id=e.get("id") or "",
                    canale=(e.get("channel") or e.get("uploader") or "").strip(),
                    durata=f"{secondi // 60}:{secondi % 60:02d}",
                    secondi=secondi,
                )
            )
        return risultati
    except Exception:
        return []


def ordina_per_rilevanza(risultati: list[Risultato],
                         parole_chiave: Iterable[str]) -> list[Risultato]:
    """Assegna il punteggio e riordina (il più pertinente in alto)."""
    for r in risultati:
        r.punteggio = _punteggio_video(r.titolo, r.canale, r.secondi, parole_chiave)
    return sorted(risultati, key=lambda r: -r.punteggio)


def ricerca_multipla(query_list: list[str], max_risultati: int = 5,
                      parole_chiave: Iterable[str] = (),
                      max_durata: int | None = None) -> list[Risultato]:
    """
    Esegue più query e unisce i risultati, eliminando i duplicati.
    È questo il cuore del "cervello": il testo genera 2-3 query diverse
    e i risultati vengono fusi per trovare la canzone più adatta.
    """
    unici: dict[str, Risultato] = {}
    for query in query_list:
        try:
            for r in cerca_youtube(query, max_risultati=max_risultati,
                                   parole_chiave=parole_chiave,
                                   max_durata=max_durata):
                if r.video_id not in unici:
                    unici[r.video_id] = r
        except ErroreRicerca:
            continue  # una query fallita non deve bloccare le altre
    risultati = list(unici.values())
    return ordina_per_rilevanza(risultati, parole_chiave)[:max_risultati]


# --------------------------------------------------------------------------
# Ricerca delle INTERPRETAZIONI (commenti, esposizioni, prediche)
# --------------------------------------------------------------------------

PAROLE_INTERPRETAZIONE = (
    "commento", "esposizione", "spiegazione", "spiegato", "studio biblico",
    "sermone", "predica", "interpretazione", "significato", "teologia",
    "biblico", "biblica", "messaggio", "meditazione", "riflessione",
    "what does", "meaning", "exposition", "commentary", "study",
)

PAROLE_CANTO = (
    "inno", "cantico", "canto", "lode", "adorazione", "hymn", "worship",
    "praise", "song", "musica", "strumentale", "karaoke", "testo canzone",
)


def _punteggio_interpretazione(titolo: str, canale: str, secondi: int | None,
                                parole_rif: Iterable[str],
                                versetto: int | None = None) -> float:
    """
    parole_rif: ["Salmo 23", "Salmi", "23", ...] - piu' e' pertinente il
    riferimento, piu' alto e' il punteggio (il video parla proprio di QUEL
    versetto).

    versetto: numero del versetto richiesto (es. 6). Se il titolo cita
    esattamente quel versetto ("Salmo 23:6", "Salmo 23,6", "Salmo 23 6")
    il punteggio sale nettamente; se cita un ALTRO versetto dello stesso
    capitolo ("Salmo 23:4") scende, perche' non e' l'interpretazione giusta.
    """
    t = (titolo or "").lower()
    c = (canale or "").lower()
    punteggio = 0.0

    for p in PAROLE_INTERPRETAZIONE:
        if p in t:
            punteggio += 3.5
            break
    for p in PAROLE_INTERPRETAZIONE:
        if p in c:
            punteggio += 1.5
            break

    # il titolo cita il versetto indicato? (es. "Salmo 23" in "Salmo 23 - ...")
    # Se il video parla di un ALTRO libro/capitolo, viene penalizzato forte.
    riferimento_pieno = ""
    for p in parole_rif:
        if p and " " in p:
            riferimento_pieno = p.lower()
            break
    libro_citato = ""
    for p in parole_rif:
        if p and " " not in p and len(p) > 3:
            libro_citato = p.lower()
            break
    capitolo_citato = str(parole_rif[-1]) if parole_rif else ""

    if riferimento_pieno and riferimento_pieno in t:
        punteggio += 9.0
    elif libro_citato and libro_citato in t:
        if capitolo_citato and capitolo_citato in t:
            punteggio += 5.0        # stesso libro e capitolo
        else:
            punteggio -= 3.0        # stesso libro, capitolo diverso
    else:
        # il video non parla del nostro passaggio: quasi nessun peso
        punteggio -= 2.0

    # ---- il VERSETTO esatto richiesto ----
    if versetto:
        _v = str(versetto)
        # numeri di versetto citati nel titolo, in ogni formato:
        # "23:6"  "23,6"  "23.6"  "23 6"  "23v6"
        _citati = re.findall(
            r"\b\d{1,3}\s*[:.,]?\s*v?\s*(\d{1,3})\b(?=\s*(?:-|–|—|\b|$))", t)
        # numeri "capitolo:versetto" espliciti (serve il capitolo per capire
        # se il numero trovato e' un versetto o un altro capitolo)
        _espliciti = re.findall(
            r"\b(\d{1,3})\s*[:.,]\s*(\d{1,3})\b", t)
        _versetti_cap = {v for (c_, v) in _espliciti if c_ == capitolo_citato}
        if _v in _versetti_cap:
            punteggio += 12.0        # parla ESATTAMENTE del nostro versetto
        elif _versetti_cap:
            # cita un altro versetto dello stesso capitolo
            punteggio -= 7.0
        else:
            # nessun "cap:vers" esplicito: cerco "capitolo versetto"
            _tutti = re.findall(r"\b\d{1,3}\s*[:.,]?\s*v?\s*(\d{1,3})\b", t)
            if _v in _tutti and capitolo_citato in t:
                punteggio += 6.0
            elif _tutti and _v not in _tutti and capitolo_citato in t:
                punteggio -= 3.0

    # è un canto, non una spiegazione?
    e_canto = any(p in t for p in PAROLE_CANTO)
    if e_canto:
        punteggio -= 4.0
        if secondi is not None and secondi < 400:
            punteggio -= 3.0

    if secondi is not None:
        if 360 <= secondi <= 2700:      # 6-45 minuti: una vera spiegazione
            punteggio += 3.0
        elif 180 <= secondi < 360:      # 3-6 minuti: sintesi
            punteggio += 1.0
        elif secondi < 120:
            punteggio -= 2.0
        elif secondi > 5400:            # 90+ minuti: predica lunga
            punteggio -= 1.0

    # solo contenuti evangelici/pentecostali
    punteggio += punteggio_confessione(titolo, canale)

    return punteggio


def _punteggio_interpretazione_con_viste(titolo: str, canale: str,
                                         secondi: int | None,
                                         parole_rif: Iterable[str],
                                         visualizzazioni: int,
                                         versetto: int | None = None) -> float:
    """Come _punteggio_interpretazione, ma tiene conto di quante persone
    hanno ascoltato il video: fra le interpretazioni che citano davvero
    il versetto, vince la piu' ascoltata."""
    punteggio = _punteggio_interpretazione(titolo, canale, secondi, parole_rif,
                                            versetto=versetto)
    if visualizzazioni > 0:
        import math
        # scala logaritmica: 100 ascolti = +3.2, 1.000 = +4.8, 18.000 = +6.8
        punteggio += min(9.0, math.log10(visualizzazioni) * 1.6 + 0.8)
    return punteggio


def query_interpretazioni(libro: str, capitolo: int, versetto: int | None,
                          riferimento: str, parole_verso: Iterable[str] = ()) -> list[str]:
    """Query per trovare studi/esposizioni sul versetto indicato."""
    query = [
        f"commento {riferimento} pentecostale",
        f"esposizione {libro} {capitolo} ADI chiesa evangelica",
        f"studio biblico {riferimento} significato",
        f"{libro} {capitolo} spiegazione versetto",
    ]
    parole = [p for p in parole_verso if p and len(p) > 4]
    if parole:
        query.append(f"{riferimento} {' '.join(parole[:3])}")
    return query[:5]


def cerca_interpretazioni(libro: str, capitolo: int, versetto: int | None,
                          riferimento: str, testo_verso: str = "",
                          max_risultati: int = 5) -> list[Risultato]:
    """
    Cerca le interpretazioni (commenti/esposizioni) del versetto indicato e
    le ordina per qualità didattica, non per canzone.
    """
    parole_verso = [p for p in re.findall(r"[A-Za-zÀ-ÿ]{5,}", testo_verso or "")][:6]
    query = query_interpretazioni(libro, capitolo, versetto, riferimento, parole_verso)
    unici: dict[str, Risultato] = {}
    for q in query:
        try:
            for r in cerca_youtube(q, max_risultati=max_risultati,
                                   parole_chiave=parole_verso):
                if r.video_id not in unici:
                    unici[r.video_id] = r
        except ErroreRicerca:
            continue

    risultati = list(unici.values())
    parole_rif = [f"{libro} {capitolo}", libro, str(capitolo)]
    for r in risultati:
        r.punteggio = _punteggio_interpretazione_con_viste(
            r.titolo, r.canale, r.secondi, parole_rif, r.visualizzazioni,
            versetto=versetto)
    risultati.sort(key=lambda x: -x.punteggio)
    return risultati[:max_risultati]
