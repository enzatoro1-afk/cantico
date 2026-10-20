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
        "musica evangelica pentecostale lode",
        "inno pentecostale",
    ],
    "Inni evangelici tradizionali": [
        "inno evangelico tradizionale lode",
        "coro evangelico lode",
    ],
    "Canzoni cristiane moderne": [
        "canzone cristiana lode",
        "musica cristiana worship",
    ],
    "Mix (tutte le proposte)": [
        "musica evangelica pentecostale lode",
        "inno pentecostale",
        "inno evangelico lode",
    ],
}


def costruisci_query(parole_chiave: Iterable[str], stile: str, extra: str = "") -> list[str]:
    """
    Unisce le parole chiave estratte con il suffisso di genere scelto.

    Esempio:
        ["amore", "fede"] + "inno pentecostale"
        -> "amore fede inno pentecostale"
    """
    base = " ".join(p for p in parole_chiave if p).strip()
    if extra:
        base = f"{base} {extra}".strip()

    suffissi = STILI.get(stile, STILI["Mix (tutte le proposte)"])
    query: list[str] = []
    for suffisso in suffissi:
        q = f"{base} {suffisso}".strip() if base else suffisso
        if q not in query:
            query.append(q)
    return query


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
    t = (titolo or "").lower()
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

    if secondi is not None:
        if 100 <= secondi <= 900:      # 1:40 - 15:00 -> la durata tipica di un inno
            punteggio += 2.0
        elif secondi < 75:              # spezzoni/intro troppo corti
            punteggio -= 3.0
        elif secondi > 3600:            # compilation lunghe
            punteggio -= 1.5

    if "- topic" in c:                  # audio ufficiale: utile ma meno "canzone"
        punteggio -= 0.5

    return punteggio


def cerca_youtube(query: str, max_risultati: int = 5,
                  parole_chiave: Iterable[str] = ()) -> list[Risultato]:
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
            params={"search_query": query, "sp": FILTRO_SOLO_VIDEO},
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        risposta.raise_for_status()
    except requests.exceptions.RequestException as exc:
        # piano B: yt-dlp (se installato) oppure messaggio d'errore
        alternativi = _cerca_con_ytdlp(query, max_risultati)
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
        alternativi = _cerca_con_ytdlp(query, max_risultati)
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
        durata = _testo(v.get("lengthText"))
        visti.add(video_id)
        risultati.append(
            Risultato(
                titolo=titolo.strip(),
                video_id=video_id,
                canale=canale.strip(),
                durata=durata.strip(),
                secondi=_durata_secondi(durata),
            )
        )

    if not risultati:
        alternativi = _cerca_con_ytdlp(query, max_risultati)
        if alternativi:
            return alternativi

    return ordina_per_rilevanza(risultati, parole_chiave)[:max_risultati]


def _cerca_con_ytdlp(query: str, max_risultati: int) -> list[Risultato]:
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
            risultati.append(
                Risultato(
                    titolo=(e.get("title") or "").strip(),
                    video_id=e.get("id") or "",
                    canale=(e.get("channel") or e.get("uploader") or "").strip(),
                    durata=str(durata) if durata else "",
                    secondi=int(durata) if isinstance(durata, (int, float)) else None,
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
                      parole_chiave: Iterable[str] = ()) -> list[Risultato]:
    """
    Esegue più query e unisce i risultati, eliminando i duplicati.
    È questo il cuore del "cervello": il testo genera 2-3 query diverse
    e i risultati vengono fusi per trovare la canzone più adatta.
    """
    unici: dict[str, Risultato] = {}
    for query in query_list:
        try:
            for r in cerca_youtube(query, max_risultati=max_risultati,
                                   parole_chiave=parole_chiave):
                if r.video_id not in unici:
                    unici[r.video_id] = r
        except ErroreRicerca:
            continue  # una query fallita non deve bloccare le altre
    risultati = list(unici.values())
    return ordina_per_rilevanza(risultati, parole_chiave)[:max_risultati]
