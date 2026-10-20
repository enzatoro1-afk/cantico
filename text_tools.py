# -*- coding: utf-8 -*-
"""
text_tools.py
=============
Strumenti sul testo che l'utente scrive:
  - correzione grammaticale/ortografica automatica (LanguageTool pubblico, gratis)
  - riconoscimento dei Salmi (con la differenza numerazione Vulgate / ebraica)
  - analisi tematica del testo (temi, tono, suggerimenti per il video)
"""

from __future__ import annotations

import re
import unicodedata

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore


def senza_accenti(testo: str) -> str:
    """Trasforma il testo in minuscolo e senza accenti: 'è' -> 'e'."""
    testo = (testo or "").lower()
    testo = unicodedata.normalize("NFKD", testo)
    return "".join(c for c in testo if not unicodedata.combining(c))

URL_LANGUAGETOOL = "https://api.languagetool.org/v2/check"
TIMEOUT_LT = 25

# Regole di LanguageTool da non applicare (solo stilistiche, non errori)
REGOLE_DA_IGNORARE = {
    "UPPERCASE_SENTENCE_START",
    "EN_QUOTES",
    "TYPOGRAPHY",
    "COMMA_PARENTHESIS_WHITESPACE",
    "WHITESPACE_RULE",
}

# Correzioni di riserva (funzionano anche senza rete)
ERRORI_FREQUENTI = {
    "perche": "perché", "percio": "perciò", "perciò": "perciò",
    "pero": "però", "gia": "già", "cosi": "così", "piu": "più",
    "puo": "può", "e'": "è", "e`": "è", "affinche": "affinché",
    "benche": "benché", "cioe": "cioè", "cio": "ciò",
    "dov'e": "dov'è", "qual'e": "qual è", "qual'e'": "qual è",
    "un po": "un po'", "sara": "sarà", "verita": "verità",
    "carita": "carità", "umilta": "umiltà", "liberta": "libertà",
    "fedelta": "fedeltà", "universita": "università",
    "attivita": "attività", "realta": "realtà",
    "possibilita": "possibilità", "difficolta": "difficoltà",
    "citta": "città", "comunita": "comunità", "quantita": "quantità",
    "meta": "metà", "pieta": "pietà", "serenita": "serenità",
    "faro": "farò", "daro": "darò", "staro": "starò",
    "a affinche": "affinché", "in realta": "in realtà",
    "di piu": "di più", "a piu": "a più", "percio'": "perciò",
    "trende": "trend", "cristiani": "cristiani",
}

# --------------------------------------------------------------------------
# 1) Correzione grammaticale
# --------------------------------------------------------------------------

def correggi_testo(testo: str) -> dict:
    """
    Corregge il testo. Restituisce:
      {"testo": testo_corretto, "problemi": [...], "metodo": "languagetool"|"regole_locali"|"nessuno"}

    Usa l'API pubblica di LanguageTool (gratuita, senza chiave).
    Se non è raggiungibile, applica le correzioni locali più comuni.
    """
    testo = (testo or "").strip()
    if not testo:
        return {"testo": testo, "problemi": [], "metodo": "nessuno"}

    # Safety: l'API pubblica non deve ricevere testi enormi
    testo_api = testo[:2000]

    if requests is not None:
        try:
            risposta = requests.post(
                URL_LANGUAGETOOL,
                data={"text": testo_api, "language": "it"},
                headers={"User-Agent": "AssistenteCanzoni/1.0"},
                timeout=TIMEOUT_LT,
            )
            if risposta.status_code == 200:
                dati = risposta.json()
                return _applica_languagetool(testo_api, dati.get("matches", []))
        except Exception:
            pass  # rete non disponibile -> si passa alle regole locali

    return _correzione_locale(testo)


def _applica_languagetool(testo: str, matches: list) -> dict:
    """Applica le correzioni suggerite (dalla fine all'inizio, per non falsare gli offset)."""
    problemi = []
    utili = []
    for m in matches:
        regola = m.get("rule", {}).get("id", "")
        sostituzioni = m.get("replacements") or []
        if regola in REGOLE_DA_IGNORARE:
            continue
        # LanguageTool restituisce [{"value": "..."}]: va estratto il testo
        valori = []
        for s in sostituzioni:
            if isinstance(s, dict):
                valore = s.get("value", "")
            else:
                valore = str(s)
            if valore:
                valori.append(valore)
        if not valori:
            continue
        utili.append((m.get("offset", 0), m.get("length", 0),
                      valori[0], regola, m.get("message", "")))
        problemi.append(
            {
                "messaggio": m.get("message", ""),
                "breve": m.get("shortMessage", ""),
                "regola": regola,
                "sostituzioni": valori[:4],
                "evidenzia": testo[m.get("offset", 0):
                                m.get("offset", 0) + m.get("length", 0)],
            }
        )

    testo_corretto = testo
    for offset, lunghezza, nuovo, _, _ in sorted(utili, key=lambda x: -x[0]):
        try:
            testo_corretto = (testo_corretto[:offset] + nuovo
                              + testo_corretto[offset + lunghezza:])
        except Exception:
            pass

    return {"testo": testo_corretto, "problemi": problemi, "metodo": "languagetool"}


def _correzione_locale(testo: str) -> dict:
    """Correzioni basate su dizionario, senza rete."""
    problemi = []
    risultato = testo
    for sbagliato, giusto in ERRORI_FREQUENTI.items():
        pattern = re.compile(r"(?<![\w'])" + re.escape(sbagliato) + r"(?![\w'])", re.IGNORECASE)

        def sostituisci(match, giusto=giusto, sbagliato=sbagliato):
            testo_match = match.group(0)
            if testo_match[:1].isupper():
                giusto = giusto[:1].upper() + giusto[1:]
            problemi.append(
                {
                    "messaggio": f'"{testo_match}" → "{giusto}"',
                    "breve": "Correzione automatica",
                    "regola": "DIZIONARIO",
                    "sostituzioni": [giusto],
                    "evidenzia": testo_match,
                }
            )
            return giusto

        risultato = pattern.sub(sostituisci, risultato)

    return {"testo": risultato, "problemi": problemi, "metodo": "regole_locali"}


# --------------------------------------------------------------------------
# 2) Riconoscimento dei Salmi
# --------------------------------------------------------------------------

# Intestazioni note dei Salmi (Vulgate -> numerazione ebraica)
SALMI_NOTI = {
    "il signore e il mio pastore": {
        "vulgate": 22, "ebraico": 23, "titolo": "Il Signore è il mio pastore",
    },
    "signore la mia luce": {
        "vulgate": 27, "ebraico": 27, "titolo": "La luce del Signore",
    },
    "crea in me o dio": {
        "vulgate": 50, "ebraico": 51, "titolo": "Crea in me, o Dio",
    },
    "venite e adoriamo": {
        "vulgate": 94, "ebraico": 95, "titolo": "Venite e adoriamo",
    },
    "non ti abbandoneri": {
        "vulgate": 21, "ebraico": 22, "titolo": "Non ti abbandonerò",
    },
    "perche mi hai abbandonato": {
        "vulgate": 21, "ebraico": 22, "titolo": "Perché mi hai abbandonato",
    },
    "signore salvami": {
        "vulgate": 3, "ebraico": 4, "titolo": "Signore, salvami",
    },
    "confesso il mio peccato": {
        "vulgate": 31, "ebraico": 32, "titolo": "Confesso il mio peccato",
    },
    " Benedetto il signore": {
        "vulgate": 102, "ebraico": 103, "titolo": "Benedetto il Signore",
    },
    "l entrare": {"vulgate": 99, "ebraico": 100, "titolo": "L'entrare"},
}

PATTERN_SALMO = re.compile(
    r"(?:\b(?:salmo|salmi|psalm|psalms)\s*\.?\s*(\d{1,3})"
    r"|\bsal\.?\s*(\d{1,3})\b"
    r"|\b(\d{1,3})\s*(?:,\s*\d{1,2})?\s*\.\s*\d{1,2}\s*\(?\s*(?:salmo|sal|psalm))",
    re.IGNORECASE,
)


def rileva_salmo(testo: str) -> dict | None:
    """
    Riconosce se il testo è (o cita) un Salmo.

    Restituisce None se non è un Salmo, altrimenti:
      {"numero": 23, "numero_vulgate": 22, "titolo": "...", "riferimento": "...",
       "fonte": "citazione" | "titolo noto"}
    """
    testo_norm = re.sub(r"[^a-z0-9à-ÿ ]", " ", senza_accenti(testo))
    testo_norm = re.sub(r"\s+", " ", testo_norm)

    match = PATTERN_SALMO.search(testo_norm)
    if match:
        numero = int(next(g for g in match.groups() if g))
        return {
            "numero": numero,
            "numero_vulgate": numero,
            "titolo": f"Salmo {numero}",
            "riferimento": f"Salmo {numero}",
            "fonte": "citazione",
        }

    for intestazione, info in SALMI_NOTI.items():
        if intestazione in testo_norm:
            return {
                "numero": info["ebraico"],
                "numero_vulgate": info["vulgate"],
                "titolo": info["titolo"],
                "riferimento": (
                    f'Salmo {info["vulgate"]} (Vulgate) / '
                    f'Salmo {info["ebraico"]} (numerazione ebraica)'
                ),
                "fonte": "titolo noto",
            }
    return None


def query_per_salmo(salmo: dict) -> list[str]:
    """Query dedicate agli inni costruiti su un determinato Salmo."""
    n = salmo.get("numero")
    nv = salmo.get("numero_vulgate")
    query = [
        f"salmo {n} inno pentecostale",
        f"inno sul salmo {n} lode",
        f"salmo {n} musica evangelica",
    ]
    if nv and nv != n:
        query.append(f"salmo {nv} inno lode")
    query.append(f"psalm {n} worship lyrics")
    return query


# --------------------------------------------------------------------------
# 3) Analisi tematica del testo
# --------------------------------------------------------------------------

TEMI = {
    "Consolazione": ["pace", "consola", "conforto", "riposo", "serenita", "calma",
                      "rifugio", "sonno", "tranquillo"],
    "Proclamazione": ["lode", "lodi", "adora", "adorazione", "esalta", "celebra",
                      "canta", "canto", "magnifica", "alleluia", "gloria"],
    "Salvezza": ["salvezza", "peccato", "grazia", "redenz", "croce", "risurrez",
                 "resurrez", "salvatore", "sacrificio", "perdono", "sacramento"],
    "Amore": ["amore", "carita", "compassione", "misericordia", "affetto",
              "amorevole", "fratello", "prossimo"],
    "Fede": ["fede", "credo", "fiducia", "confessa", "testimonianza", "confidare"],
    "Preghiera": ["preghiera", "prega", "orazione", "ascolta", "signore", "dio",
                  "abbocca", "invoca", "custodi", "veglia"],
    "Coraggio": ["coraggio", "forte", "non temere", "ardimento", "prova",
                 "resisti", "sii forte", "non avere paura"],
    "Guarigione": ["guarigione", "sana", "cura", "ferita", "malattia", "sanare"],
    "Speranza": ["speranza", "attendo", "attesa", "futuro", "promessa", "verrà",
                 "confida", "confido", "aspetta", "aspettare", "aiuto",
                 "soccorso", "scudo", "spererò"],
    "Umiltà": ["umilta", "servo", "piccolo", "ultimo", "lavate", "polvere"],
    "Paternità": ["padre", "abba", "figlio", "padre nostro"],
}


def analizza_testo(testo: str, parole_chiave: list[str] | None = None) -> dict:
    """
    Analizza il testo: temi principali, tono consigliato, salmo rilevato,
    durata e formato del video suggeriti.
    """
    testo_norm = re.sub(r"[^a-z0-9à-ÿ ]", " ", senza_accenti(testo))
    testo_norm = re.sub(r"\s+", " ", testo_norm)
    parole = list(parole_chiave or [])

    temi = []
    punteggi: dict[str, int] = {}
    for tema, keywords in TEMI.items():
        hits = [k for k in keywords if k in testo_norm]
        if hits:
            punteggi[tema] = len(hits) + sum(1 for p in parole if p in keywords)
            temi.append(tema)
    temi.sort(key=lambda t: -punteggi[t])

    parole_testo = len(testo_norm.split())
    if "Consolazione" in temi or "Preghiera" in temi:
        tono = "Contemplativo e consolatorio"
    elif "Proclamazione" in temi or "Coraggio" in temi:
        tono = "Proclamatorio e incoraggiante"
    elif "Salvezza" in temi:
        tono = "Dichiarativo e forte"
    else:
        tono = "Riflessivo e spirituale"

    if parole_testo <= 12:
        durata = "15-20 secondi"
        formato = "Frase d'impatto"
    elif parole_testo <= 30:
        durata = "20-30 secondi"
        formato = "Versetto + domanda"
    else:
        durata = "30-45 secondi"
        formato = "Versetto + invito alla reflection"

    salmo = rileva_salmo(testo)

    return {
        "temi": temi[:3],
        "tono": tono,
        "durata_video": durata,
        "formato_post": formato,
        "salmo": salmo,
        "num_parole": parole_testo,
        "testo": testo,
    }


# --------------------------------------------------------------------------
# 4) Spiegazione dettagliata di una canzone proposta
# --------------------------------------------------------------------------

def spiega_canzone(titolo: str, canale: str, durata: str, secondi: int | None,
                   parole_chiave: list[str], temi: list[str] | None = None) -> list[str]:
    """
    Spiega in modo leggibile perché una canzone è stata proposta.
    """
    motivi: list[str] = []
    titolo_low = (titolo or "").lower()
    canale_low = (canale or "").lower()

    for kw in parole_chiave:
        if kw.lower() in titolo_low:
            motivi.append(f'il titolo contiene la parola chiave «{kw}»')
        elif kw.lower() in canale_low:
            motivi.append(f'il canale è legato al tema «{kw}»')

    for s in ("pentecostale", "pentecostal", "lode", "inno", "evangelico", "evangelica",
              "adorazione", "cristiana", "worship", "canto"):
        if s in titolo_low:
            motivi.append(f'gli inni di lode evangelica sono esplicitamente nel titolo («{s}»)')
            break

    if secondi is not None:
        if 100 <= secondi <= 900:
            motivi.append(
                f"la durata ({durata}) è perfetta per un video TikTok da 15-30 secondi"
            )
        elif secondi < 100:
            motivi.append(f"durata breve ({durata}): ottima come intro/hook")
        else:
            motivi.append(f"durata lunga ({durata}): meglio se scegli un estratto")

    for tema in (temi or []):
        if tema.lower() in titolo_low or tema.lower() in canale_low:
            motivi.append(f"corrisponde al tema «{tema}» del tuo testo")
            break

    if not motivi:
        motivi.append("è un brano di musica evangelica che può accompagnare il tuo testo")

    return motivi[:4]
