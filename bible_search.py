# -*- coding: utf-8 -*-
"""
bible_search.py
===============
Cerca il VERSETTO BIBLICO che meglio corrisponde a una parola, una frase o un
pensiero scritto dall'utente.

Corpus: "Sacra Bibbia - Versione Riveduta 2020" (traduzione protestante /
evangelica, non cattolica), gratuita e pubblica: scaricata una volta sola e
messa in cache.

Il motore lavora per CONCETTI:
  il tuo pensiero viene scomposto in concetti ("perdonami", "peccato"...) e
  per ogni concetto si cercano i verbi biblici equivalenti ("perdonami" ->
  perdona, rimette, misericordia...). Un versetto che contiene DUE concetti
  distinti vince su un versetto che ne contiene uno solo: e' cosi' che
  "perdonami perche' ho peccato" trova i versetti che parlano DI PERDONO E
  DI PECCATO, non le liste di offerte del Levitico.
"""

from __future__ import annotations

import bisect
import json
import math
import os
import re
import unicodedata

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore

URL_BIBBIA = ("https://raw.githubusercontent.com/thiagobodruk/bible/"
              "master/json/it_irb20.json")
URL_MIRROR = ("https://cdn.jsdelivr.net/gh/thiagobodruk/bible@master/"
              "json/it_irb20.json")
NOME_CACHE = "cache_bibbia.json"
TIMEOUT = 90
HEADERS = {"User-Agent": "AssistenteCanzoni/1.0"}

NOME_TRADUZIONE = "Sacra Bibbia - Versione Riveduta 2020 (traduzione evangelica)"

LIBRI_IT = [
    "Genesi", "Esodo", "Levitico", "Numeri", "Deuteronomio", "Giosuè", "Giudici",
    "Rut", "1 Samuele", "2 Samuele", "1 Re", "2 Re", "1 Cronache", "2 Cronache",
    "Esdra", "Neemia", "Ester", "Giob", "Salmi", "Proverbi", "Ecclesiaste",
    "Cantico dei Cantici", "Isaia", "Geremia", "Lamentazioni", "Ezechiele",
    "Daniele", "Osea", "Gioele", "Amos", "Obadia", "Giona", "Michea", "Naum",
    "Habacuc", "Sofonia", "Aggeo", "Zaccaria", "Malachia", "Matteo", "Marco",
    "Luca", "Giovanni", "Atti", "Romani", "1 Corinzi", "2 Corinzi", "Galati",
    "Efesini", "Filippesi", "Colossesi", "1 Tessalonicesi", "2 Tessalonicesi",
    "1 Timoteo", "2 Timoteo", "Tito", "Filemone", "Ebrei", "Giacomo", "1 Pietro",
    "2 Pietro", "1 Giovanni", "2 Giovanni", "3 Giovanni", "Giuda", "Apocalisse",
]

# --------------------------------------------------------------------------
# TEMI: concetto -> parole dell'utente + radici bibliche equivalenti
# --------------------------------------------------------------------------

TEMI = {
    "amore": {
        "query": ["ama", "amare", "amavo", "amorevole", "amorevoli", "carita",
                  "ami", "amiamo", "amata", "amato", "amanti", "amante",
                  "amore", "amerei", "amerei"],
        "stems": ["amor", "amav", "amant", "amiam", "amaz", "carit"],
    },
    "perdono": {
        "query": ["perdonami", "perdoni", "perdono", "perdonare", "perdonato",
                  "misericordia", "misericordioso", "misericordie", "rimetti",
                  "rimettere", "scusa", "scusare", "assoluzione", "remissione",
                  "perdonate", "perdonava"],
        "stems": ["perdon", "misericord", "rimett", "propizia", "scus", "assolv",
                  "remiss"],
    },
    "colpa": {
        "query": ["sbaglio", "sbagli", "sbagliato", "sbaglio", "errore", "errori",
                  "colpa", "colpe", "peccato", "peccati", "peccatore", "vergogna",
                  "fallimento", "fallito", "pentimento", "confessa",
                  "trasgressione", "iniquita", "peccare", "ho peccato"],
        "stems": ["peccat", "colpa", "errore", "iniquit", "trasgress", "confess",
                  "pentiment", "sbagli", "peccator", "vergogn"],
    },
    "paura": {
        "query": ["paura", "paure", "timore", "temi", "temo", "ansia", "ansie",
                  "angoscia", "spavento", "terrore", "preoccupazione",
                  "spaventato", "ho paura", "temere"],
        "stems": ["paur", "timore", "temer", "temi", "ansia", "angoscia",
                  "spavent", "terror", "tremit"],
    },
    "speranza": {
        "query": ["speranza", "spero", "spera", "speriamo", "attesa", "attendo",
                  "fiducia", "futuro", "aspettando", "speravo", "spererò",
                  "spererai", "confido"],
        "stems": ["speran", "spera", "attend", "attesa", "fiducia", "aspett",
                  "avvenir", "promessa", "confid"],
    },
    "pace": {
        "query": ["pace", "pacifica", "pacifico", "sereno", "serenita", "calma",
                  "tranquillo", "riposo", "quiete", "in pace"],
        "stems": ["pace", "pacific", "seren", "calma", "tranquill", "riposo",
                  "quiet"],
    },
    "fede": {
        "query": ["fede", "credo", "crede", "credenza", "fiducia", "confesso",
                  "credere", "creduto", "fiducioso"],
        "stems": ["fede", "creder", "crede", "credut", "confess", "fiducia"],
    },
    "salvezza": {
        "query": ["salvezza", "salvatore", "salva", "salvami", "redenzione",
                  "sacrificio", "croce", "risurrezione", "vita", "eterna",
                  "salvato", "salvezza"],
        "stems": ["salvezza", "salvator", "salva", "redenz", "sacrific", "croce",
                  "risurrez", "vita", "etern"],
    },
    "guida": {
        "query": ["pastore", "guida", "conduci", "conduce", "strada", "cammino",
                  "sentiero", "via", "direzione", "condurre", "condotto"],
        "stems": ["pastor", "guid", "conduc", "strad", "cammin", "sentier", "via"],
    },
    "luce": {
        "query": ["luce", "luminoso", "risplende", "risplender", "tenebre",
                  "oscurita", "notte", "luminosa"],
        "stems": ["luce", "lumin", "risplend", "tenebr", "oscur", "notte"],
    },
    "preghiera": {
        "query": ["preghiera", "prega", "pregare", "preghiamo", "ascolta",
                  "ascoltami", "invoca", "invocare", "custodi", "veglia",
                  "ascoltaci"],
        "stems": ["preghier", "preg", "ascolt", "invoc", "custod", "vegli",
                  "cried", "grida"],
    },
    "perdimento": {
        "query": ["perdo", "perdere", "perso", "perdita", "abbandono",
                  "abbandonato", "abbandonerei", "abbandonera", "solo", "smarrito",
                  "lacrime", "pianto", "dolore", "sofferenza", "tristezza",
                  "abbandonarmi", "mi abbandoni"],
        "stems": ["perd", "abbandon", "lacrime", "pianto", "dolore", "soffr",
                  "tristez", "smarrit"],
    },
    "famiglia": {
        "query": ["fratello", "sorella", "fratelli", "padre", "madre", "figlio",
                  "figlia", "famiglia", "figli", "padre nostro", "fratello mio"],
        "stems": ["fratell", "sorell", "padre", "madre", "figli", "famigl"],
    },
    "verita": {
        "query": ["verita", "vero", "parola", "parole", "testimonia",
                  "testimonianza", "verace"],
        "stems": ["verita", "vero", "parol", "testimon"],
    },
    "servizio": {
        "query": ["servire", "servizio", "opera", "opere", "lavoro", "missione",
                  "testimone", "testimonianza"],
        "stems": ["serv", "opera", "mission", "testimon", "lavor"],
    },
    "battesimo": {
        "query": ["battesimo", "battezzato", "battezzare", "acqua", "immersione"],
        "stems": ["battes", "battezz", "immers"],
    },
    "coraggio": {
        "query": ["coraggio", "forte", "fortezza", "non temere", "non avere paura",
                  "ardimento", "prova"],
        "stems": ["coragg", "fortez", "forti", "ardiment"],
    },
}

STOPWORDS = {
    "a", "ad", "al", "alla", "alle", "allo", "ai", "gli", "loro", "io", "tu",
    "egli", "ella", "noi", "voi", "mi", "ti", "ci", "vi", "si", "ne", "ma",
    "ed", "che", "chi", "non", "piu", "per", "perche", "come", "con", "senza",
    "tra", "fra", "del", "dello", "della", "dei", "degli", "delle", "dal",
    "dalla", "su", "sul", "sulla", "nel", "nella", "nei", "nelle", "suo",
    "sua", "suoi", "sue", "mio", "mia", "tuo", "tua", "questo", "questa",
    "questi", "queste", "quello", "quella", "sono", "sei", "e", "stato",
    "essere", "ha", "ho", "hanno", "fare", "fa", "fanno", "puo", "deve",
    "devo", "dobbiamo", "cosa", "cose", "modo", "luogo", "parte", "punto",
    "sempre", "mai", "molto", "poco", "troppo", "meno", "anche", "ora",
    "oggi", "ieri", "domani", "poi", "anzi", "tuttavia", "percio", "infatti",
    "ecco", "quando", "dove", "tempo", "giorni", "giorno", "vita", "mondo",
    "casa", "citta", "parola", "parole", "verso", "versi", "salmo", "salmi",
    "coro", "signore", "dio", "gesu", "cristo", "san", "santa", "santo",
    "va", "sto", "stai", "ancora", "gia", "tutto", "tutti", "tutte", "altro",
    "altra", "altri", "altre", "ogni", "quando", "oggi", "sempre",
}

SUFFISSI_STEM = [
    "ando", "endo", "ano", "ino", "ato", "uto", "ito", "ale", "ico", "ina",
    "ai", "ei", "ar", "er", "ir", "o", "a", "e", "i",
]


def _norm(testo: str) -> str:
    testo = (testo or "").lower()
    testo = unicodedata.normalize("NFKD", testo)
    return "".join(c for c in testo if not unicodedata.combining(c))


def stem(parola: str) -> str:
    """Stemming leggero dell'italiano."""
    parola = _norm(parola)
    for suffisso in SUFFISSI_STEM:
        if len(parola) - len(suffisso) >= 4 and parola.endswith(suffisso):
            return parola[:-len(suffisso)]
    return parola


def _cache_path() -> str:
    try:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), NOME_CACHE)
        with open(path, "a", encoding="utf-8"):
            pass
        return path
    except Exception:
        import tempfile
        return os.path.join(tempfile.gettempdir(), NOME_CACHE)


def scarica_bibbia() -> list[dict] | None:
    """Scarica (o recupera dalla cache) la Bibbia in italiano."""
    percorso = _cache_path()
    if os.path.exists(percorso):
        try:
            with open(percorso, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    if requests is None:
        return None

    for url in (URL_BIBBIA, URL_MIRROR):
        try:
            risposta = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            if risposta.status_code != 200:
                continue
            risposta.encoding = "utf-8"
            dati = risposta.json()
            try:
                with open(percorso, "w", encoding="utf-8") as f:
                    json.dump(dati, f, ensure_ascii=False)
            except Exception:
                pass
            return dati
        except Exception:
            continue
    return None


class MotoreBibbia:
    """Motore di ricerca dei versetti (costruito una volta, riusato)."""

    def __init__(self):
        self.versetti: list[dict] = []
        self.indice: dict[str, list[int]] = {}
        self.chiavi_ordinate: list[str] = []
        self.caricato = False
        self.errore: str | None = None
        self._concetto_cache: dict[str, tuple[list[str], float, str | None]] = {}

    # -- caricamento ------------------------------------------------------
    def carica(self) -> bool:
        if self.caricato:
            return True
        dati = scarica_bibbia()
        if not dati:
            self.errore = ("Non sono riuscito a scaricare il testo biblico. "
                           "Controlla la connessione e riprova.")
            return False
        try:
            self.versetti = self._prepara(dati)
            self.indice = {}
            for i, v in enumerate(self.versetti):
                for s in set(v["stemi"]):
                    self.indice.setdefault(s, []).append(i)
            self.chiavi_ordinate = sorted(self.indice)
            self.caricato = True
            self.errore = None
            return True
        except Exception as exc:  # pragma: no cover
            self.errore = f"Errore nel preparare il testo biblico: {exc}"
            return False

    @staticmethod
    def _prepara(dati: list) -> list[dict]:
        versetti: list[dict] = []
        for i_libro, libro in enumerate(dati):
            nome = (LIBRI_IT[i_libro] if i_libro < len(LIBRI_IT)
                    else (libro.get("name") or "").strip())
            for i_cap, capitolo in enumerate(libro.get("chapters") or [], start=1):
                for i_vers, testo in enumerate(capitolo, start=1):
                    testo = (testo or "").strip()
                    if not testo:
                        continue
                    parole = re.findall(r"[a-z]{3,}", _norm(testo))
                    versetti.append({
                        "libro": nome,
                        "capitolo": i_cap,
                        "versetto": i_vers,
                        "riferimento": f"{nome} {i_cap},{i_vers}",
                        "testo": testo,
                        "parole": parole,
                        "stemi": [stem(p) for p in parole],
                    })
        return versetti

    # -- indice per prefisso ----------------------------------------------
    def _versi_per_prefisso(self, prefisso: str) -> list[int]:
        """Versetti che contengono una parola che inizia con 'prefisso'."""
        if not prefisso:
            return []
        chiavi = self.chiavi_ordinate
        i = bisect.bisect_left(chiavi, prefisso)
        j = bisect.bisect_right(chiavi, prefisso + "\uffff")
        risultato: list[int] = []
        for k in chiavi[i:j]:
            risultato.extend(self.indice[k])
        return risultato

    def _idf(self, df: int) -> float:
        n = max(1, len(self.versetti))
        return math.log(1 + n / (1 + max(0, df)))

    def _concetto(self, parola: str) -> tuple[list[str], float, str | None]:
        """
        Trasforma una parola del pensiero in un "concetto":
        (radici bibliche equivalenti, peso idf, nome del tema).
        """
        if parola in self._concetto_cache:
            return self._concetto_cache[parola]

        s_parola = stem(parola)
        for nome_tema, dati in TEMI.items():
            for q in dati["query"]:
                if parola == q or s_parola == stem(q):
                    radici = list(dati["stems"])
                    df = len(set(sum((self._versi_per_prefisso(r) for r in radici), [])))
                    peso = self._idf(df)
                    risultato = (radici, peso, nome_tema)
                    self._concetto_cache[parola] = risultato
                    return risultato

        # parola libera: si cerca la sua radice nel testo biblico
        df = len(self._versi_per_prefisso(s_parola))
        peso = self._idf(df) if df else 1.0
        risultato = ([s_parola], peso, None)
        self._concetto_cache[parola] = risultato
        return risultato

    # -- ricerca ----------------------------------------------------------
    def cerca(self, testo: str, max_risultati: int = 5) -> list[dict]:
        """Restituisce i versetti più affini al testo."""
        if not self.caricato and not self.carica():
            return []

        parole_q = [p for p in re.findall(r"[a-z]{3,}", _norm(testo))
                    if p not in STOPWORDS]
        if not parole_q:
            parole_q = re.findall(r"[a-z]{3,}", _norm(testo))
        if not parole_q:
            return []

        concetti = []
        for parola in parole_q:
            radici, peso, tema = self._concetto(parola)
            if not radici:
                continue
            versi = set()
            for r in radici:
                versi.update(self._versi_per_prefisso(r))
            if versi:
                concetti.append({
                    "parola": parola,
                    "radici": radici,
                    "peso": peso,
                    "tema": tema,
                    "versi": versi,
                })
        if not concetti:
            return []

        punteggi: dict[int, float] = {}
        concetti_trovati: dict[int, list[str]] = {}
        temi_trovati: dict[int, set] = {}

        for concetto in concetti:
            for idx in concetto["versi"]:
                punteggi[idx] = punteggi.get(idx, 0.0) + concetto["peso"]
                concetti_trovati.setdefault(idx, []).append(concetto["parola"])
                if concetto["tema"]:
                    temi_trovati.setdefault(idx, set()).add(concetto["tema"])

        risultati = []
        for idx, punteggio in punteggi.items():
            v = self.versetti[idx]
            n_concetti = len(set(concetti_trovati[idx]))
            bonus = 1 + 0.85 * max(0, n_concetti - 1)
            n_parole = max(12, len(v["parole"]))
            finale = (punteggio * bonus) / math.sqrt(n_parole)
            risultati.append({
                "riferimento": v["riferimento"],
                "testo": v["testo"],
                "libro": v["libro"],
                "capitolo": v["capitolo"],
                "versetto": v["versetto"],
                "punteggio": round(finale, 3),
                "parole_collegate": sorted(set(concetti_trovati[idx])),
                "temi": sorted(temi_trovati.get(idx, set())),
                "concetti": n_concetti,
            })

        risultati.sort(key=lambda x: -x["punteggio"])
        return risultati[:max_risultati]


_MOTORE: MotoreBibbia | None = None


def motore() -> MotoreBibbia:
    global _MOTORE
    if _MOTORE is None:
        _MOTORE = MotoreBibbia()
        _MOTORE.carica()
    return _MOTORE


def cerca_versetti(testo: str, max_risultati: int = 5) -> list[dict]:
    """Comodo: cerca i versetti più adatti a un testo."""
    return motore().cerca(testo, max_risultati)
