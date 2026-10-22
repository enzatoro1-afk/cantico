# -*- coding: utf-8 -*-
"""
riflessione.py
==============
Due passaggi che vengono DOPO l'interpretazione del versetto:

1) LA RIFLESSIONE
   L'IA scrive una riflessione personale (in prima persona) partendo dal
   testo del versetto e dall'interpretazione che l'app ha appena scritto.

2) IL POST TIKTOK
   La stessa riflessione viene RIDOTTA in un post pronto da pubblicare:
   - HOOK   : la frase da mettere a schermo nei primi 3 secondi
   - CORPO  : 3 righe da dire/mostrare, una per idea
   - CAPTION: la caption (l'app ci aggiunge gli hashtag)
   - CTA    : l'invito finale (commenta / salva / condividi)

Se l'IA non risponde, NIENTE si perde:
- la riflessione viene ricavata dalla sezione "DALLA VOCE DI DIO AL NOSTRO
  CUORE" dell'interpretazione (che c'e' sempre);
- il post viene costruito in locale, tagliando la riflessione.
"""

from __future__ import annotations

import re

try:
    from ai_client import (chiave_gemini_da_secrets, interpreta_con_ia,
                           interpreta_gemini, interpreta_gratis)
except Exception:  # il file potrebbe non essere ancora sul server
    def chiave_gemini_da_secrets() -> str:
        return ""

    def interpreta_gemini(prompt, chiave="", modello="", timeout=120):
        return {"testo": "", "errore": "modulo IA non disponibile"}

    def interpreta_gratis(prompt, timeout=120, tentativi=1):
        return {"testo": "", "errore": "modulo IA non disponibile"}

    def interpreta_con_ia(prompt, chiave="", modello="", url_api="",
                          timeout=90):
        return {"testo": "", "errore": "modulo IA non disponibile"}


# --------------------------------------------------------------------------
# I PROMPT
# --------------------------------------------------------------------------

PROMPT_RIFLESSIONE = """Sei un credente evangelico pentecostale che ha appena studiato una Parola e ci si e' fermato sopra. Scrivi una RIFLESSIONE PERSONALE per un amico che sta scorrendo TikTok: parla a LUI, in prima persona, come se fosse una voce amica.

RIFERIMENTO BIBLICO: {riferimento}
TESTO BIBLICO:
{testo_versetto}

INTERPRETAZIONE (scrivi la riflessione SU QUESTA, non su un'altra):
{interpretazione}

REGOLE:
- 2 o 3 paragrafi, 120-200 parole in tutto. Niente titoli, niente liste.
- Scrivi in prima persona ("ho letto", "mi ha colpito", "oggi mi sono accorto").
- Parti SEMPRE e SOLO dal versetto e dall'interpretazione qui sopra.
- Usa i nomi ESATTAMENTE come compaiono nel testo (se il testo dice "Gesu", scrivi "Gesu").
- Non inventare episodi, luoghi, numeri o altri passaggi biblici.
- Non citare canzoni, inni o titoli di brani: le canzoni le cerca l'app.
- Tono semplice e concreto, parole di tutti i giorni, niente paroloni.
- Non usare emoji e non usare titoli in MAIUSCOLO.
- Chiudere con una frase che resti nel cuore e che si possa cantare.

Alla fine scrivi SEMPRE questa riga (l'app la usa per gli hashtag):
'Parole chiave: Parola1, Parola2, Parola3'"""


# Prompt unico: riflessione + riduzione per il post, in una sola risposta.
# Serve per non fare due chiamate all'IA (la gratuita e' lenta).
PROMPT_RIFLESSIONE_E_POST = """Sei un creator evangelico che prepara un video per TikTok. Prima scrivi una RIFLESSIONE PERSONALE sul versetto, poi la RIDUCI in un post pronto da pubblicare.

RIFERIMENTO BIBLICO: {riferimento}
TESTO BIBLICO:
{testo_versetto}

INTERPRETAZIONE (la riflessione si scrive SU QUESTA, non su un'altra):
{interpretazione}

--- PARTE 1: LA RIFLESSIONE ---
- 2 o 3 paragrafi, 120-200 parole, in prima persona ("ho letto", "mi ha toccato").
- Parti SEMPRE e SOLO dal versetto e dall'interpretazione qui sopra.
- Usa i nomi ESATTAMENTE come compaiono nel testo; non inventare episodi, luoghi, numeri o altri versetti.
- Non citare canzoni, inni o titoli di brani: le canzoni le cerca l'app.
- Tono semplice e concreto, parole di tutti i giorni, niente paroloni, niente emoji.
- Chiudi con una frase che resti nel cuore e che si possa cantare.

--- PARTE 2: IL POST TIKTOK (riduzione della riflessione) ---
Rispondi con questo formato esatto, e non aggiungere altro:
HOOK: <massimo 7 parole: la frase che appare a schermo nei primi 3 secondi>
CORPO:
- <riga 1: una frase, massimo 10 parole>
- <riga 2: una frase, massimo 10 parole>
- <riga 3: una frase, massimo 10 parole>
- <riga 4: una frase, massimo 10 parole>
- <riga 5: una frase, massimo 10 parole>
- <riga 6: una frase, massimo 10 parole>
- <riga 7: una frase, massimo 10 parole>
- <riga 8: una frase, massimo 10 parole>
- <riga 9: una frase, massimo 10 parole>
- <riga 10: una frase, massimo 10 parole>
CAPTION: <massimo 220 caratteri: la caption, con dentro il versetto o un pezzo di versetto, e un invito. Niente hashtag: li aggiunge l'app.>
CTA: <una riga sola: cosa fare (commenta, salva, condividi, scrivi nei commenti)>
GIORNO: <il giorno della settimana migliore per pubblicare: lunedi, martedi, mercoledi, giovedi, venerdi, sabato o domenica>
FASCIA: <la fascia oraria: mattina presto, mattina, pausa pranzo, pomeriggio, sera o notte>
MOTIVO: <due frasi: perche' questo giorno e questa fascia funzionano per un contenuto spirituale come questo>
CONSIGLIO: <una riga sola: un accorgimento pratico per la pubblicazione>

Regole della parte 2: solo italiano, frasi semplici, niente emoji, niente titoli.
Il CORPO e' lo script che il creator LEGGE AD ALTA VOCE durante il video:
- 8-12 righe, una idea per riga, in ordine (la prima riprende l'HOOK, poi
  spieghi, poi arrivi alla risposta, poi chiudi con l'invito);
- ogni riga si capisce da sola, anche se la persona guarda solo il video;
- non ripetere l'HOOK nella prima riga: comincia subito con il cuore;
- NON citare altri versetti ne' canzoni.
GIORNO e FASCIA devono essere una scelta concreta, non "dipende": considera il tono (un contenuto di consolazione funziona meglio la sera o nel fine settimana, un contenuto di incoraggiamento meglio la mattina).

Alla fine della parte 1 (non alla fine di tutto) scrivi la riga:
'Parole chiave: Parola1, Parola2, Parola3'"""


PROMPT_POST = """Sei un creator che prepara un video per TikTok. Devi RIDURRE la riflessione qui sotto in un post pronto da pubblicare: breve, diretto, adatto a un video di 20-30 secondi.
RIFERIMENTO BIBLICO: {riferimento}
TESTO BIBLICO:
{testo_versetto}

RIFLESSIONE DA RIDURRE:
{riflessione}

Rispondi ESATTAMENTE con questo formato (nient'altro):
HOOK: <massimo 7 parole: la frase che appare a schermo nei primi 3 secondi>
CORPO:
- <riga 1: una frase, massimo 10 parole>
- <riga 2: una frase, massimo 10 parole>
- <riga 3: una frase, massimo 10 parole>
- <riga 4: una frase, massimo 10 parole>
- <riga 5: una frase, massimo 10 parole>
- <riga 6: una frase, massimo 10 parole>
- <riga 7: una frase, massimo 10 parole>
- <riga 8: una frase, massimo 10 parole>
- <riga 9: una frase, massimo 10 parole>
- <riga 10: una frase, massimo 10 parole>
CAPTION: <massimo 220 caratteri: la caption, con dentro il versetto o un pezzo di versetto, e un invito. Niente hashtag: li aggiunge l'app.>
CTA: <una riga sola: cosa fare (commenta, salva, condividi, scrivi nei commenti)>
GIORNO: <il giorno della settimana migliore per pubblicare: lunedi, martedi, mercoledi, giovedi, venerdi, sabato o domenica>
FASCIA: <la fascia oraria: mattina presto, mattina, pausa pranzo, pomeriggio, sera o notte>
MOTIVO: <due frasi: perche' questo giorno e questa fascia funzionano per un contenuto spirituale come questo>
CONSIGLIO: <una riga sola: un accorgimento pratico per la pubblicazione>

REGOLE:
- Solo italiano, frasi semplici, niente emoji, niente titoli.
- Il CORPO e' lo script che il creator LEGGE AD ALTA VOCE: 8-12 righe, una idea
  per riga, in ordine. Ogni riga si capisce da sola. Non ripetere l'HOOK
  nella prima riga.
- Non citare altri versetti, non citare canzoni, non inventare nomi.
- GIORNO e FASCIA devono essere una scelta concreta, non "dipende": considera il tono (consolazione -> sera o fine settimana, incoraggiamento -> mattina).
- Scrivi tutto in italiano, senza prefazioni e senza ragionamenti."""


# Quando pubblicare: l'IA guarda il contenuto del post e dice il momento
# giusto (giorno della settimana + fascia oraria) e PERCHE'.
PROMPT_MOMENTO = """Sei un social media manager per creator cristiani. Devi dire QUANDO pubblicare questo video su TikTok, e PERCHE'.

RIFERIMENTO BIBLICO: {riferimento}
TEMA DEL POST: {tema}
TESTO A SCHERMO: {hook}
CONTENUTO:
{contenuto}

Rispondi ESATTAMENTE con questo formato (nient'altro):
GIORNO: <il giorno della settimana migliore: lunedi, martedi, mercoledi, giovedi, venerdi, sabato o domenica>
FASCIA: <la fascia oraria: mattina presto, mattina, pausa pranzo, pomeriggio, sera, notte>
MOTIVO: <due frasi: perche' questo giorno e questa fascia funzionano per un contenuto spirituale come questo>
CONSIGLIO: <una riga sola: un accorgimento pratico per la pubblicazione (es. "tTuesday sera: le persone ascoltano gli inni mentre si preparano al lavoro", oppure "il sabato mattina funziona meglio per i contenuti di consolazione")>

REGOLE:
- Solo italiano, massimo 25 parole per il MOTIVO, niente emoji, niente titoli.
- Il GIORNO e la FASCIA devono essere una scelta concreta, non "dipende".
- Considera il tono del contenuto: un contenuto di consolazione o di conforto funziona meglio la sera o nel fine settimana; un contenuto di incoraggiamento funziona meglio la mattina.
- Non citare canzoni ne' altri versetti."""


# --------------------------------------------------------------------------
# La riflessione di ripiego (senza IA): presa dall'interpretazione
# --------------------------------------------------------------------------

SEZIONI_INTERPRETAZIONE = (
    "DALLA VOCE DI DIO",
    "PER LA LODE",
    "IL SIGNIFICATO",
)

# tutte le intestazioni possibili dell'interpretazione (1., 2., 3., ...)
_TUTTE_SEZIONI = (
    "IL TESTO",
    "IL CONTESTO",
    "IL SIGNIFICATO",
    "DALLA VOCE DI DIO",
    "PER LA LODE",
)


def _estrai_sezione(interpretazione: str, intestazioni) -> str:
    """
    Prende il testo che segue una delle intestazioni indicate.

    Le intestazioni dell'interpretazione sono numerate ("4. DALLA VOCE DI DIO
    AL NOSTRO CUORE"), quindi cerco l'inizio di riga: cosi' non taglio a
    meta' parola e non lascio dentro il titolo ("AL NOSTRO CUORE").
    Se piu' sezioni ci sono, prendo la PIU' LUNGA (quella piu' corposa).
    """
    t = (interpretazione or "").strip()
    if not t:
        return ""
    _migliore = ""
    for _h in intestazioni:
        # l'intestazione deve stare a inizio riga (eventualmente numerata
        # e/o tra asterischi: "**4. DALLA VOCE DI DIO AL NOSTRO CUORE**")
        _m = re.search(r"^[ \t]*(?:\*\*)?[ \t]*(?:\d+[.)][ \t]*)?\**[ \t]*" +
                       re.escape(_h) + r"\b[^\n]*$", t,
                       flags=re.IGNORECASE | re.M)
        if not _m:
            continue
        _inizio = _m.end()
        # la sezione finisce dove comincia un'altra intestazione
        _fine = len(t)
        for _h2 in _TUTTE_SEZIONI:
            if _h2 == _h:
                continue
            _m2 = re.search(r"^[ \t]*(?:\*\*)?[ \t]*(?:\d+[.)][ \t]*)?\**[ \t]*" +
                            re.escape(_h2) + r"\b[^\n]*$", t[_inizio:],
                            flags=re.IGNORECASE | re.M)
            if _m2:
                _fine = min(_fine, _inizio + _m2.start())
        _pezzo = t[_inizio:_fine].strip()
        _pezzo = re.sub(r"\*\*", "", _pezzo)
        _pezzo = re.sub(r"\n{2,}", "\n", _pezzo).strip()
        if len(_pezzo) > len(_migliore):
            _migliore = _pezzo
    return _migliore


def riflessione_dalla_interpretazione(interpretazione: str) -> str:
    """
    Una riflessione anche SENZA IA: prende la parte piu' cuore-vivente
    dell'interpretazione (la voce di Dio al nostro cuore) e la pulisce.
    Serve a non lasciare mai l'utente a mani vuote.
    """
    _t = _estrai_sezione(interpretazione, SEZIONI_INTERPRETAZIONE)
    if not _t:
        _t = re.sub(r"\*\*", "", (interpretazione or "")).strip()
    _t = re.sub(r"Parole chiave:.*$", "", _t, flags=re.IGNORECASE | re.S)
    _t = re.sub(r"\s+", " ", _t).strip()
    if len(_t) > 900:
        _t = _t[:900].rsplit(" ", 1)[0] + "."
    return _t


def _parole_chiave_riflessione(testo: str, numero: int = 3) -> list[str]:
    """La riga 'Parole chiave: A, B, C' che l'IA scrive in fondo."""
    m = re.findall(r"parole\s+chiave\s*:\s*(.+)", testo or "",
                   flags=re.IGNORECASE)
    if not m:
        return []
    parole = re.split(r"[,;·•]|\s+e\s+", m[-1])
    out = [p.strip(" .*-\n\t") for p in parole]
    return [p for p in out if 2 < len(p) < 30][:numero]


# --------------------------------------------------------------------------
# La chiamata all'IA (Gemini -> OpenAI -> IA gratuita)
# --------------------------------------------------------------------------

def _chiedi(prompt: str, chiave_gemini: str = "", chiave_openai: str = "",
            min_chars: int = 150) -> dict:
    """
    Chiede un testo all'IA migliore disponibile. Non solleva mai: se tutti
    i servizi falliscono torna un dizionario con l'errore.

    Ordine: Gemini (veloce, con la chiave) -> OpenAI -> IA gratuita
    (l'ultima e' lenta: deve aspettare ~30 s, quindi va per ultima).
    """
    _problemi: list[str] = []

    _k = (chiave_gemini or "").strip() or (chiave_gemini_da_secrets() or "").strip()
    if _k:
        _r = interpreta_gemini(prompt, chiave=_k, timeout=120)
        if _r.get("testo") and len(_r["testo"]) >= min_chars:
            return {"testo": _r["testo"], "fonte": _r.get("fonte", "Gemini"),
                    "errore": None}
        _problemi.append("Gemini: " + str(_r.get("errore") or
                                          "risposta troppo corta"))
    else:
        _problemi.append("Gemini: nessuna chiave")

    if (chiave_openai or "").strip():
        _r = interpreta_con_ia(prompt, chiave=chiave_openai)
        if _r.get("testo") and len(_r["testo"]) >= min_chars:
            return {"testo": _r["testo"], "fonte": _r.get("fonte", "ChatGPT"),
                    "errore": None}
        _problemi.append("OpenAI: " + str(_r.get("errore") or
                                           "risposta non utilizzabile"))

    # ultima risorsa: la IA gratuita (1 tentativo, cosi' non si aspetta
    # un minuto quando e' occupata)
    _r = interpreta_gratis(prompt, tentativi=1)
    if _r.get("testo") and len(_r["testo"]) >= min_chars:
        return {"testo": _r["testo"], "fonte": _r.get("fonte", "IA gratuita"),
                "errore": None}
    _problemi.append("IA gratuita: " + str(_r.get("errore") or
                                           "risposta non utilizzabile"))

    return {"testo": "", "fonte": "", "errore": " | ".join(_problemi)}


# --------------------------------------------------------------------------
# 1) LA RIFLESSIONE
# --------------------------------------------------------------------------

def genera_riflessione(testo_versetto: str, interpretazione: str,
                        riferimento: str = "", chiave_gemini: str = "",
                        chiave_openai: str = "") -> dict:
    """
    L'IA scrive la riflessione personale sul versetto gia' interpretato.

    Restituisce:
      {"testo": str, "parole_chiave": [...], "fonte": str, "errore": str|None}
    """
    _fallback = riflessione_dalla_interpretazione(interpretazione)
    if not (testo_versetto or "").strip() and not (interpretazione or "").strip():
        return {"testo": "", "parole_chiave": [], "fonte": "",
                "errore": "Non c'e' niente su cui scrivere la riflessione."}

    _prompt = PROMPT_RIFLESSIONE.format(
        riferimento=riferimento or "il passaggio",
        testo_versetto=(testo_versetto or "").strip() + "\n",
        interpretazione=(interpretazione or "").strip()[:6000],
    )
    _r = _chiedi(_prompt, chiave_gemini, chiave_openai, min_chars=180)
    if _r.get("testo"):
        _kw = _parole_chiave_riflessione(_r["testo"])
        _testo = re.sub(r"Parole chiave:.*$", "", _r["testo"], flags=re.S)
        _testo = _testo.strip()
        return {"testo": _testo, "parole_chiave": _kw,
                "fonte": _r.get("fonte", "IA"), "errore": None}

    # niente IA: riflessione di ripiego presa dall'interpretazione
    return {"testo": _fallback, "parole_chiave": [],
            "fonte": "dall'interpretazione",
            "errore": _r.get("errore", "")}


# --------------------------------------------------------------------------
# 2) IL POST TIKTOK (la riduzione)
# --------------------------------------------------------------------------

def _post_locale(riflessione: str, testo_versetto: str = "") -> dict:
    """
    Riduzione fatta in locale (quando l'IA non risponde).

    Il CORPO viene spezzato in righe brevi da leggere ad alta voce, come
    lo script di un video da 20-30 secondi.
    """
    _r = re.sub(r"\s+", " ", (riflessione or "")).strip()
    # 1) le frasi
    _frasi = [f.strip() for f in re.split(r"(?<=[.!?])\s+", _r) if f.strip()]
    # 2) ogni frase lunga diventa piu' righe da 8-12 parole
    _righe: list[str] = []
    for _f in _frasi:
        _parti = _f.split(", ")
        _buff = ""
        for _p in _parti:
            _cand = (_buff + " " + _p).strip() if _buff else _p.strip()
            if len(_cand.split()) > 12 and _buff:
                _righe.append(_buff.strip())
                _buff = _p.strip()
            else:
                _buff = _cand
        if _buff.strip():
            _righe.append(_buff.strip())
    if not _righe:
        _righe = ["La Parola di oggi parla al tuo cuore."]
    _corpo = _righe[:12]
    _hook = " ".join((_r.split()[:7])) or "Fermati un secondo"
    _cap = _r[:220].strip()
    if testo_versetto and testo_versetto not in _cap:
        _cap = (testo_versetto[:80].strip() + " - " + _r).strip()[:220]
    return {
        "hook": _hook,
        "corpo": _corpo,
        "caption": _cap,
        "cta": "Scrivi nei commenti cosa ti ha toccato",
        "fonte": "riduzione locale",
        "errore": None,
    }


def _estrai_blocco(testo: str, etichetta: str) -> str:
    m = re.search(etichetta + r"\s*:\s*(.+?)(?=\n\s*(?:HOOK|CORPO|CAPTION|CTA|"
                  r"GIORNO|FASCIA|MOTIVO|CONSIGLIO)\s*:|\Z)",
                  testo or "", flags=re.IGNORECASE | re.S)
    return m.group(1).strip() if m else ""


def riduci_per_post(riflessione: str, testo_versetto: str = "",
                    riferimento: str = "", chiave_gemini: str = "",
                    chiave_openai: str = "") -> dict:
    """
    Riduce la riflessione in un post TikTok.

    Restituisce:
      {"hook": str, "corpo": [str, str, str], "caption": str, "cta": str,
       "fonte": str, "errore": str|None}
    """
    if not (riflessione or "").strip():
        return _post_locale("", testo_versetto)

    _prompt = PROMPT_POST.format(
        riferimento=riferimento or "il passaggio",
        testo_versetto=(testo_versetto or "").strip() + "\n",
        riflessione=(riflessione or "").strip()[:4000],
    )
    _r = _chiedi(_prompt, chiave_gemini, chiave_openai, min_chars=60)
    if not _r.get("testo"):
        _p = _post_locale(riflessione, testo_versetto)
        _p["errore"] = _r.get("errore")
        return _p

    _t = _r["testo"]
    _hook = _estrai_blocco(_t, "HOOK").strip().strip('"')
    _corpo_raw = _estrai_blocco(_t, "CORPO")
    _corpo = [re.sub(r"^[\-\*\u2022]\s*", "", r).strip()
              for r in _corpo_raw.split("\n") if r.strip()]
    _corpo = [c for c in _corpo if c][:12]
    _caption = _estrai_blocco(_t, "CAPTION").strip().strip('"')
    _cta = _estrai_blocco(_t, "CTA").strip()

    if not _hook or not _caption or len(_corpo) < 2:
        _p = _post_locale(riflessione, testo_versetto)
        _p["errore"] = _r.get("errore")
        return _p

    _post = {"hook": _hook, "corpo": _corpo, "caption": _caption,
             "cta": _cta, "fonte": _r.get("fonte", "IA"), "errore": None}
    _m = _momento_dalla_risposta(_t)
    if _m:
        _post["momento"] = _m
    return _post


# --------------------------------------------------------------------------
# QUANDO PUBBLICARE: il momento giusto, scelto sull'umore del contenuto
# --------------------------------------------------------------------------

GIORNI = ("lunedi", "martedi", "mercoledi", "giovedi", "venerdi", "sabato",
          "domenica")
FASCE = ("mattina presto", "mattina", "pausa pranzo", "pomeriggio", "sera",
         "notte")

# le fasce orarie abbinate a ogni momento della giornata
FASCIA_ORARIO = {
    "mattina presto": "07:00",
    "mattina": "09:30",
    "pausa pranzo": "12:30",
    "pomeriggio": "16:30",
    "sera": "20:30",
    "notte": "22:30",
}


def _momento_locale(hook: str = "", contenuto: str = "") -> dict:
    """
    Momento suggerito SENZA IA: si guarda il tono del testo.
    - parole di conforto/consolazione -> sera
    - parole di incoraggiamento/lode -> mattina
    """
    _t = ((hook or "") + " " + (contenuto or "")).lower()
    _comfort = ("consol", "sola", "paura", "dolore", "piang", "speranza",
                "attesa", "coraggio", "forza", "resto", "pace", "notte")
    _lode = ("gioia", "alleluia", "lode", "cantare", "esulta", "celebr",
             "trionf", "vittoria")
    _n_comfort = sum(1 for p in _comfort if p in _t)
    _n_lode = sum(1 for p in _lode if p in _t)
    if _n_lode > _n_comfort:
        return {"giorno": "domenica", "fascia": "mattina",
                "orario": "08:30",
                "motivo": ("domenica mattina: chi ascolta un inno presto "
                           "lo porta con se tutto il giorno"),
                "consiglio": "pubblica presto la domenica, prima delle "
                             "uscite e delle adunanze"}
    return {"giorno": "venerdi", "fascia": "sera", "orario": "20:30",
            "motivo": ("venerdi sera: la gente e' stanca della settimana e "
                       "apre il contenuto per ritrovare consolazione"),
            "consiglio": "togli volume e musica bassa: e' il momento della "
                         "parola, non dello spettacolo"}


def momento_migliore(hook: str = "", contenuto: str = "", tema: str = "",
                      riferimento: str = "", chiave_gemini: str = "",
                      chiave_openai: str = "") -> dict:
    """
    Dice il giorno e la fascia oraria giusti per pubblicare questo post,
    e il perche'.

    Restituisce:
      {"giorno": str, "fascia": str, "orario": "HH:MM", "motivo": str,
       "consiglio": str, "fonte": str, "errore": str|None}
    """
    if not ((hook or "").strip() or (contenuto or "").strip()):
        return {"giorno": "", "fascia": "", "orario": "", "motivo": "",
                "consiglio": "", "fonte": "",
                "errore": "Non c'e' nessun post da pianificare."}

    _prompt = PROMPT_MOMENTO.format(
        riferimento=riferimento or "il passaggio",
        tema=tema or "fede e lode",
        hook=(hook or "").strip(),
        contenuto=(contenuto or "").strip()[:3000],
    )
    _r = _chiedi(_prompt, chiave_gemini, chiave_openai, min_chars=60)
    if not _r.get("testo"):
        _m = _momento_locale(hook, contenuto)
        _m["fonte"] = "suggerimento automatico"
        _m["errore"] = _r.get("errore")
        return _m

    _t = _r["testo"]
    _giorno = _estrai_blocco(_t, "GIORNO").strip().lower().strip(".")
    _fascia = _estrai_blocco(_t, "FASCIA").strip().lower().strip(".")
    _motivo = _estrai_blocco(_t, "MOTIVO").strip()
    _consiglio = _estrai_blocco(_t, "CONSIGLIO").strip()

    # normalizza il giorno (l'IA puo' scrivere "martedì" con l'accento)
    _g = None
    for _gg in GIORNI:
        if _giorno.startswith(_gg[:6]):
            _g = _gg
            break
    if not _g:
        _m = _momento_locale(hook, contenuto)
        _m["fonte"] = "suggerimento automatico"
        return _m

    # normalizza la fascia
    _f = None
    for _ff in FASCE:
        if _fascia.startswith(_ff[:6]):
            _f = _ff
            break
    if not _f:
        _f = "sera"

    return {"giorno": _g, "fascia": _f,
            "orario": FASCIA_ORARIO.get(_f, "20:30"),
            "motivo": _motivo, "consiglio": _consiglio,
            "fonte": _r.get("fonte", "IA"), "errore": None}


# --------------------------------------------------------------------------
# TUTTO IN UNA VOLTA: riflessione + riduzione per il post
# --------------------------------------------------------------------------

def genera_riflessione_e_post(testo_versetto: str, interpretazione: str,
                               riferimento: str = "", chiave_gemini: str = "",
                               chiave_openai: str = "") -> dict:
    """
    Una sola chiamata all'IA che fa entrambe le cose:
    scrive la riflessione e la riduce subito in un post TikTok.

    Restituisce:
      {"riflessione": str, "parole_chiave": [...],
       "post": {"hook","corpo","caption","cta","fonte","errore"},
       "fonte": str, "errore": str|None}
    """
    _interpretazione = (interpretazione or "").strip()
    if not (testo_versetto or "").strip() and not _interpretazione:
        return {"riflessione": "", "parole_chiave": [],
                "post": _post_locale("", testo_versetto),
                "fonte": "", "errore": "Non c'e' niente su cui scrivere."}

    _prompt = PROMPT_RIFLESSIONE_E_POST.format(
        riferimento=riferimento or "il passaggio",
        testo_versetto=(testo_versetto or "").strip() + "\n",
        interpretazione=_interpretazione[:6000],
    )
    _r = _chiedi(_prompt, chiave_gemini, chiave_openai, min_chars=180)
    if not _r.get("testo"):
        # niente IA: riflessione dall'interpretazione + riduzione locale
        _rif = riflessione_dalla_interpretazione(_interpretazione)
        _p = _post_locale(_rif, testo_versetto)
        _p["errore"] = _r.get("errore")
        return {"riflessione": _rif, "parole_chiave": [],
                "post": _p, "fonte": "dall'interpretazione",
                "errore": _r.get("errore")}

    _t = _r["testo"]
    # la parte 1 (riflessione) sta PRIMA di "HOOK:"
    _i = re.search(r"^\s*HOOK\s*:", _t, flags=re.IGNORECASE | re.M)
    _rif = (_t[:_i.start()] if _i else _t).strip()
    _rif = re.sub(r"Parole chiave:.*$", "", _rif, flags=re.IGNORECASE | re.S)
    _rif = _rif.strip()
    _kw = _parole_chiave_riflessione(_t)

    _post = _post_dalla_risposta(_t)
    if _post is None:
        _post = _post_locale(_rif, testo_versetto)
    return {"riflessione": _rif, "parole_chiave": _kw, "post": _post,
            "fonte": _r.get("fonte", "IA"), "errore": None}


def _post_dalla_risposta(testo: str):
    """Legge il blocco HOOK/CORPO/CAPTION/CTA. None se non e' leggibile."""
    _hook = _estrai_blocco(testo, "HOOK").strip().strip('"')
    _corpo_raw = _estrai_blocco(testo, "CORPO")
    _corpo = [re.sub(r"^[\-\*\u2022]\s*", "", r).strip()
              for r in _corpo_raw.split("\n") if r.strip()]
    _corpo = [c for c in _corpo if c][:12]
    _caption = _estrai_blocco(testo, "CAPTION").strip().strip('"')
    _cta = _estrai_blocco(testo, "CTA").strip()
    if not _hook or not _caption or len(_corpo) < 2:
        return None
    _post = {"hook": _hook, "corpo": _corpo, "caption": _caption,
             "cta": _cta, "fonte": "IA", "errore": None}
    # il momento giusto per pubblicare (arriva nella stessa risposta)
    _m = _momento_dalla_risposta(testo)
    if _m:
        _post["momento"] = _m
    return _post


def _momento_dalla_risposta(testo: str):
    """Legge GIORNO/FASCIA/MOTIVO/CONSIGLIO dalla stessa risposta dell'IA."""
    _giorno = _estrai_blocco(testo, "GIORNO").strip().lower().strip(".")
    _fascia = _estrai_blocco(testo, "FASCIA").strip().lower().strip(".")
    _motivo = _estrai_blocco(testo, "MOTIVO").strip()
    _consiglio = _estrai_blocco(testo, "CONSIGLIO").strip()
    if not (_giorno or _fascia):
        return None
    _g = None
    for _gg in GIORNI:
        if _giorno.startswith(_gg[:6]):
            _g = _gg
            break
    _f = None
    for _ff in FASCE:
        if _fascia.startswith(_ff[:6]):
            _f = _ff
            break
    if not _g and not _f:
        return None
    _g = _g or "venerdi"
    _f = _f or "sera"
    return {"giorno": _g, "fascia": _f,
            "orario": FASCIA_ORARIO.get(_f, "20:30"),
            "motivo": _motivo, "consiglio": _consiglio,
            "fonte": "IA", "errore": None}
