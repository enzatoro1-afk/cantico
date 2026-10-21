# -*- coding: utf-8 -*-
"""
ai_client.py
============
Chiamata diretta a un'IA (OpenAI / compatibili) per l'interpretazione
dottrinale del versetto.

E' FACOLTATIVO: senza chiave API l'app continua a funzionare con il motore
"predicazioni reali" (trascrizioni YouTube dei ministri/pastori evangelici).
"""

from __future__ import annotations

import json
import re

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore

MODEL_PREDEFINITO = "gpt-4o-mini"
URL_PREDEFINITO = "https://api.openai.com/v1/chat/completions"


def chiave_da_secrets() -> str:
    """Cerca la chiave nelle secrets di Streamlit (se configurate)."""
    try:
        import streamlit as st
        return (st.secrets.get("OPENAI_API_KEY", "") or "").strip()
    except Exception:
        return ""


def interpreta_con_ia(prompt: str, chiave: str = "", modello: str = "",
                       url_api: str = "", timeout: int = 90) -> dict:
    """
    Invia il prompt all'IA e restituisce:
      {"testo": "...", "parole_chiave": [...], "errore": None|str,
       "modello": "...", "fonte": "ChatGPT (API)"}

    Se manca la chiave o la rete fallisce, NON solleva: restituisce
    l'errore nel dizionario, così l'app può ripiegare sul motore YouTube.
    """
    if requests is None:
        return {"testo": "", "parole_chiave": [], "errore": "requests non installato",
                "modello": "", "fonte": "ChatGPT (API)"}

    chiave = (chiave or chiave_da_secrets() or "").strip()
    if not chiave:
        return {"testo": "", "parole_chiave": [],
                "errore": "Nessuna chiave API: aggiungila nella casella "
                          "'Chiave API OpenAI' in alto.",
                "modello": "", "fonte": "ChatGPT (API)"}

    modello = modello or MODEL_PREDEFINITO
    url_api = url_api or URL_PREDEFINITO

    corpo = {
        "model": modello,
        "messages": [
            {"role": "system",
             "content": "Sei un assistente biblico di dottrina Cristiana "
                        "Evangelica Pentecostale (linea ADI / Assemblee di Dio). "
                        "Rispondi in italiano, con titoli chiari, senza "
                        "preamboli. NON citare canzoni, inni o titoli di "
                        "brani: curi solo il significato del testo."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.4,
        "max_tokens": 1600,
    }

    try:
        risposta = requests.post(
            url_api,
            headers={"Authorization": f"Bearer {chiave}",
                     "Content-Type": "application/json"},
            data=json.dumps(corpo).encode("utf-8"),
            timeout=timeout,
        )
        if risposta.status_code != 200:
            return {"testo": "", "parole_chiave": [],
                    "errore": f"IA: errore {risposta.status_code} "
                              f"({risposta.text[:180]})",
                    "modello": modello, "fonte": "ChatGPT (API)"}
        dati = risposta.json()
        testo = (dati["choices"][0]["message"]["content"] or "").strip()
        return {"testo": testo, "parole_chiave": [], "errore": None,
                "modello": modello, "fonte": f"ChatGPT ({modello})"}
    except Exception as exc:
        return {"testo": "", "parole_chiave": [],
                "errore": f"IA non raggiungibile: {exc}",
                "modello": modello, "fonte": "ChatGPT (API)"}


def link_chatgpt(prompt: str) -> str:
    """Link che apre ChatGPT con il prompt gia' scritto (web app)."""
    from urllib.parse import quote_plus
    return "https://chatgpt.com/?q=" + quote_plus(prompt)


# --------------------------------------------------------------------------
# GOOGLE GEMINI (piano gratuito di Google AI Studio)
# --------------------------------------------------------------------------
# La chiave si prende gratis su https://aistudio.google.com/apikey
# Il piano gratuito dà centinaia di richieste al giorno.

URL_GEMINI = "https://generativelanguage.googleapis.com/v1beta/models"
# I modelli disponibili cambiano spesso: l'app li prova in ordine e usa
# il primo che risponde.
MODELLI_GEMINI = ("gemini-3.8-flash", "gemini-flash-latest",
                  "gemini-2.5-flash", "gemini-3.5-flash",
                  "gemini-flash-lite-latest")
LINK_CHIAVE_GEMINI = "https://aistudio.google.com/apikey"


def _percorso_chiave_server() -> str:
    """File (nel container, MAI su GitHub) dove ricordare la chiave."""
    import os
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        ".chiave_gemini_server.json")


def _chiave_dal_server() -> str:
    """Legge la chiave ricordata sul server (se c'e')."""
    try:
        import json
        import os
        p = _percorso_chiave_server()
        if not os.path.exists(p):
            return ""
        with open(p, "r", encoding="utf-8") as f:
            return str((json.load(f) or {}).get("GEMINI_API_KEY", "")).strip()
    except Exception:
        return ""


def ricorda_chiave_gemini(chiave: str) -> bool:
    """
    Salva la chiave sul server, cosi' non va reinserita a ogni sessione
    (vale per tutti gli utenti dell'app). Il file NON e' su GitHub.
    """
    chiave = (chiave or "").strip()
    if not chiave:
        return False
    try:
        import json
        with open(_percorso_chiave_server(), "w", encoding="utf-8") as f:
            json.dump({"GEMINI_API_KEY": chiave}, f)
        return True
    except Exception:
        return False


def dimentica_chiave_gemini() -> bool:
    """Cancella la chiave ricordata sul server."""
    try:
        import os
        p = _percorso_chiave_server()
        if os.path.exists(p):
            os.remove(p)
            return True
    except Exception:
        pass
    return False


def chiave_gemini_da_secrets() -> str:
    """
    Cerca la chiave Gemini nei secrets di Streamlit, poi nel file locale
    .streamlit/secrets.toml, poi nel server (chiave ricordata), poi
    nell'ambiente.
    Nomi accettati: GEMINI_API_KEY, GOOGLE_API_KEY (quello usato dalla
    SDK ufficiale 'google-genai').
    """
    for nome in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        try:
            import streamlit as st
            v = (st.secrets.get(nome, "") or "").strip()
            if v:
                return v
        except Exception:
            pass
        v = (__import__("os").environ.get(nome, "") or "").strip()
        if v:
            return v
    # file dei secrets locale ( utile quando l'app gira sul PC)
    try:
        import os
        import tomllib
        _p = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           ".streamlit", "secrets.toml")
        if os.path.exists(_p):
            with open(_p, "rb") as f:
                _d = tomllib.load(f)
            for nome in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
                v = str(_d.get(nome, "") or "").strip()
                if v:
                    return v
    except Exception:
        pass
    # chiave ricordata sul server (per l'app online)
    return _chiave_dal_server()


def _gemini_con_sdk(prompt: str, chiave: str, modello: str,
                    timeout: int) -> str:
    """
    Usa la SDK ufficiale 'google-genai' (la stessa del tuo esempio).
    Restituisce il testo della risposta, oppure "" se fallisce.
    """
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        return ""
    try:
        client = genai.Client(api_key=chiave)
        config = types.GenerateContentConfig(
            system_instruction=SISTEMA_BIBLICO,
            temperature=0.45,
            max_output_tokens=4000,
        )
        risposta = client.models.generate_content(
            model=modello,
            contents=prompt,
            config=config,
        )
        return (risposta.text or "").strip()
    except Exception:
        return ""


def interpreta_gemini(prompt: str, chiave: str = "", modello: str = "",
                      timeout: int = 120) -> dict:
    """
    Chiede l'interpretazione a Google Gemini (piano gratuito).
    Se la chiave manca o il modello non risponde, prova il modello successivo.
    Non solleva mai: l'errore torna nel dizionario.
    """
    vuoto = {"testo": "", "parole_chiave": [], "modello": "", "fonte": "Gemini"}
    if requests is None:
        return {**vuoto, "errore": "requests non installato"}

    chiave = (chiave or chiave_gemini_da_secrets() or "").strip()
    if not chiave:
        return {**vuoto, "errore": "Nessuna chiave Gemini: inseriscila in alto "
                                   "(e' gratis su aistudio.google.com/apikey)."}

    modelli = (modello,) if modello else MODELLI_GEMINI
    ultimo = ""
    for m in modelli:
        # 1) SDK ufficiale 'google-genai' (quella di google)
        _sdk = _gemini_con_sdk(prompt, chiave, m, timeout)
        if len(_sdk) > 120:
            return {"testo": _pulisci_giornale(_sdk), "parole_chiave": [],
                    "errore": None, "modello": m,
                    "fonte": f"Google Gemini ({m})"}
        # 2) fallback: HTTP diretto (funziona anche senza la SDK)
        try:
            risposta = requests.post(
                f"{URL_GEMINI}/{m}:generateContent",
                params={"key": chiave},
                json={
                    "systemInstruction": {"parts": [{"text": SISTEMA_BIBLICO}]},
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.45,
                        "maxOutputTokens": 4000,
                    },
                },
                timeout=timeout,
            )
            if risposta.status_code == 200:
                dati = risposta.json()
                parti = (dati.get("candidates") or [{}])[0].get(
                    "content", {}).get("parts", [])
                testo = "\n".join(p.get("text", "") for p in parti).strip()
                testo = _pulisci_giornale(testo)
                if len(testo) > 120:
                    return {"testo": testo, "parole_chiave": [],
                            "errore": None, "modello": m,
                            "fonte": f"Google Gemini ({m})"}
                ultimo = f"{m}: risposta troppo corta"
            elif risposta.status_code == 400 and "API key" in risposta.text:
                return {**vuoto, "errore": "Chiave Gemini non valida."}
            elif risposta.status_code == 404:
                ultimo = f"{m}: modello non disponibile"
                continue
            else:
                ultimo = (f"{m}: errore {risposta.status_code} "
                           f"({risposta.text[:120]})")
        except Exception as exc:
            ultimo = f"{m}: {exc}"

    return {**vuoto, "errore": ultimo or "Gemini non raggiungibile"}


# --------------------------------------------------------------------------
# IA GRATUITA SENZA CHIAVE API
# --------------------------------------------------------------------------
# Pollinations AI: risponde senza registrazione e senza chiave.
# Limite: 1 risposta ogni ~30 secondi per IP (si risolve aspettando e
# riprovare). Se fallisce l'app ripiega sul motore di studio.

URL_POLLINATIONS = "https://text.pollinations.ai/"
MODELLO_POLLINATIONS = "openai"

SISTEMA_BIBLICO = (
    "Sei un MAESTRO DELLA SCRITTURA: un biblista evangelico pentecostale "
    "(linea ADI / Assemblee di Dio) con trent'anni di insegnamento, che "
    "spiega la Bibbia con rigore dottrinale, profondita' teologica e "
    "calore di cuore. Scrivi in ITALIANO, con titoli in grassetto.\n\n"
    "COME PARLI:\n"
    "- profondita' teologica reale: spiega il cuore del testo, non le "
    "parole in superficie;\n"
    "- conosci la Scrittura e la dottrina della grazia: mostrati, ma senza "
    "pedanteria;\n"
    "- scrivi come parli a un fratello davanti al fuoco, non come un "
    "manuale;\n"
    "- parole che si possano CANTARE: ritmo, concretezza, affettuosita'.\n\n"
    "REGOLE ASSOLUTE (non violarle):\n"
    "1) Parti SEMPRE e SOLO dal testo biblico che ti do: spiega QUEL testo, "
    "non un altro.\n"
    "2) NON INVENTARE MAI:\n"
    "   - usa i nomi ESATTAMENTE come compaiono nel testo (se il testo dice "
    "'Gesù', scrivi 'Gesù': non sostituire il nome con un altro);\n"
    "   - non aggiungere luoghi, persone, eventi, numeri o dettagli che non "
    "sono nel testo;\n"
    "   - se citi un altro passaggio biblico, cito' solo quelli di cui sei "
    "certissimo; meglio nessuno che uno sbagliato;\n"
    "   - se non sai qualcosa, non scriverlo.\n"
    "3) Non citare canzoni, inni o titoli di brani musicali.\n"
    "4) Scrivi TUTTE le sezioni richieste, senza troncare la risposta.\n"
    "5) Rispondi DIRETTAMENTE con il testo in italiano: non mostrare le tue "
    "ragionazioni, non dire 'we need to', non usare l'inglese."
)

# Sistema BREVE per l'IA gratuita: i modelli piccoli (quello senza chiave)
# se ricevono un prompt di sistema pieno di regole "ragionano" fino a
# esaurire i token e non scrivono MAI la risposta finale (arriva solo il
# loro ragionamento in inglese). Con un sistema breve rispondono subito,
# in italiano e con tutte le sezioni.
SISTEMA_BREVE = (
    "Sei un biblista evangelico pentecostale. Rispondi in ITALIANO, "
    "direttamente con il testo dell'interpretazione, senza mostrare le tue "
    "ragionazioni e senza prefazioni."
)


def parole_chiave_dall_ia(testo: str, numero: int = 3) -> list[str]:
    """
    Legge la riga finale 'Parole chiave: Fortezza, Salvezza, Fedelta'
    che l'IA scrive: sono le parole che l'IA stessa ritiene piu' forti
    per il versetto. Servono per cercare la canzone piu' adatta.
    Se la riga non c'e', prendo le parole piu' significative del testo
    scritto dall'IA (cosi' la canzone resta legata all'interpretazione).
    """
    t = (testo or "")
    m = re.findall(r"parole\s+chiave\s*:\s*(.+)", t, flags=re.IGNORECASE)
    if m:
        grezze = re.split(r"[,;·•]|\s+e\s+", m[-1])
        parole = [p.strip(" .*-\n\t") for p in grezze]
        parole = [p for p in parole if 2 < len(p) < 30]
        if parole:
            return parole[:numero]

    # fallback: uso il lessico spirituale del progetto (gia' calibrato:
    # pesa "fede", "salvezza", "grazia"... e scarta le parole generiche)
    try:
        from studio_biblico import estrai_parole_chiave_spirituali
        _k = estrai_parole_chiave_spirituali(t, numero)
        if _k:
            return _k
    except Exception:
        pass

    # ultimo ripiego: le parole piu' frequenti del testo
    esclusi = {
        "questo", "questa", "questi", "quelle", "quello", "signore",
        "nostro", "vostro", "loro", "sono", "essere", "aveva", "hanno",
        "tutti", "anche", "quando", "perche", "mentre", "adesso", "dove",
        "come", "della", "delle", "dello", "degli", "abbiamo", "possono",
        "versetto", "testo", "passaggio", "parola", "parole", "significato",
        "contesto", "studio", "esposizione", "dottrina", "scrittura",
        "interpretazione", "pentecostale", "evangelica", "vangelo", "dice",
        "questo", "questa", "cioe", "cio", "puo", "deve", "vuole",
        "egli", "loro", "dove", "come", "anche", "sono", "essere", "hanno",
        "questi", "quelle", "quello", "tutti", "ogni", "suo", "sua", "dei",
        "delle", "della", "dello", "degli", "nel", "per", "con", "non",
        "una", "uno", "gli", "dai", "dal", "della", "verso", "ancora",
        "riguardo", "proprio", "stesso", "soltanto", "appena", "tutto",
    }
    conteggio: dict[str, int] = {}
    for p in re.findall(r"[A-Za-zÀ-ÿ]{4,}", t):
        p = p.lower()
        if p in esclusi:
            continue
        conteggio[p] = conteggio.get(p, 0) + 1
    ordinati = sorted(conteggio.items(), key=lambda kv: (-kv[1], kv[0]))
    return [p for p, _ in ordinati[:numero]]


def qualita_ia(testo: str) -> bool:
    """
    Controlla che la risposta dell'IA sia utilizzabile.
    I modelli piccoli scrivono a volte in italiano "rotto" (parole inventate,
    frasi spezzate): meglio ricadere sul motore di studio che mostrare
    una pagina di nonsenso.
    """
    t = (testo or "").strip()
    if len(t) < 500:
        return False
    # 0) NON deve essere il ragionamento del modello (in inglese)
    if re.match(r"^\s*(we need to|we must|our task|the user)", t,
                flags=re.IGNORECASE):
        return False
    if '"reasoning"' in t[:200] or '"role":"assistant"' in t[:200]:
        return False
    # 1) deve avere almeno 3 delle 5 sezioni richieste
    sezioni = ("IL TESTO", "IL CONTESTO", "IL SIGNIFICATO", "PER LA LODE",
               "DALLA VOCE DI DIO")
    trovate = sum(1 for s in sezioni if s in t.upper())
    if trovate < 3:
        return False
    # 2) non deve ripetere lo stesso blocco (segno di output rotto)
    righe = [r.strip() for r in t.split("\n") if len(r.strip()) > 40]
    if len(righe) >= 3 and len(set(righe)) < len(righe) * 0.7:
        return False
    # 3) troppe parole lunghe e sconosciute = italiano rotto
    parole = re.findall(r"[a-zA-Zà-ÿ]{13,}", t.lower())
    if len(parole) > 6 and len(set(parole)) / len(parole) < 0.5:
        return False
    return True


def _estrai_testo_ia(crudo: str) -> str:
    """
    Estrae il testo VERO dalla risposta dell'IA.
    I modelli "ragionanti" possono rispondere in tre modi diversi:
      1) testo semplice in italiano (quello che vogliamo);
      2) JSON con "reasoning" ma senza "content": e' il loro ragionamento
         in inglese, NON la risposta -> la scarto;
      3) JSON con "content" (o "choices"): prendo il content.
    """
    grezzo = (crudo or "").strip()
    if not grezzo:
        return ""
    if grezzo.startswith("{"):
        try:
            d = json.loads(grezzo)
        except Exception:
            d = None
        if isinstance(d, dict):
            # 3) content
            for chiave in ("content", "text", "answer", "message"):
                v = d.get(chiave)
                if isinstance(v, str) and len(v.strip()) > 50:
                    return _pulisci_giornale(v)
                if isinstance(v, dict):
                    for k2 in ("content", "text"):
                        v2 = v.get(k2)
                        if isinstance(v2, str) and len(v2.strip()) > 50:
                            return _pulisci_giornale(v2)
            # formato OpenAI
            scelte = d.get("choices")
            if isinstance(scelte, list) and scelte:
                msg = scelte[0].get("message") or {}
                v = msg.get("content")
                if isinstance(v, str) and len(v.strip()) > 50:
                    return _pulisci_giornale(v)
            # 2) solo reasoning: NON e' la risposta
            return ""
    # testo semplice: se sembra un ragionamento inglese, scartalo
    if re.match(r"^\s*we need to\b", grezzo, flags=re.IGNORECASE):
        return ""
    return _pulisci_giornale(grezzo)


def scegli_versetto_ia(riflessione: str, candidati: list[dict],
                       chiave_gemini: str = "", chiave_openai: str = "") -> dict:
    """
    Chiede all'IA quale dei versetti candidati parla davvero alla riflessione
    dell'utente (il versetto giusto, non quello con le parole simili).

    Restituisce {"indice": int|None, "motivo": str, "errore": str|None}
    """
    if not candidati:
        return {"indice": None, "motivo": "", "errore": "nessun candidato"}
    _elenco = "\n".join(
        f"{i+1}. {c.get('riferimento','')}: {c.get('testo','')[:220]}"
        for i, c in enumerate(candidati))
    _prompt = (
        "L'utente ha scritto questa riflessione personale sulla Parola di Dio:\n"
        f"«{riflessione}»\n\n"
        "Ecco i versetti candidati trovati per parole simili:\n"
        f"{_elenco}\n\n"
        "Scegli il versetto che parla VERAMENTE alla riflessione dell'utente. "
        "ATTENZIONE al senso: se un versetto parla del contrario (es. "
        "l'utente dice 'Dio non abbandona' e il versetto dice 'Dio l'ha "
        "abbandonato'), NON va bene.\n"
        "Se nessuno dei candidati va bene, indica il versetto GIUSTO che "
        "parla alla riflessione, con il riferimento esatto "
        "(es. 'Salmo 23,1' o 'Giovanni 3,16').\n\n"
        "Rispondi ESATTAMENTE con:\n"
        "NUMERO: <il numero del candidato scelto, oppure 0 se nessuno va "
        "bene>\n"
        "RIFERIMENTO: <il riferimento esatto del versetto giusto, "
        "scrivi 'nessuno' se non hai un versetto migliore>\n"
        "MOTIVO: <una frase che spiega perche' questo versetto parla alla "
        "riflessione>"
    )
    _r = _chiedi_ia_testo(_prompt, chiave_gemini, chiave_openai)
    _testo = (_r or "").strip()
    if not _testo:
        return {"indice": None, "motivo": "", "riferimento": "",
                "errore": "IA non disponibile"}
    import re as _re
    _m = _re.search(r"NUMERO\s*:\s*(\d+)", _testo, _re.IGNORECASE)
    _rf = _re.search(r"RIFERIMENTO\s*:\s*([^\n]+)", _testo, _re.IGNORECASE)
    _mot = _re.search(r"MOTIVO\s*:\s*(.+)", _testo, _re.IGNORECASE)
    _n = int(_m.group(1)) if _m else 0
    _motivo = _mot.group(1).strip() if _mot else ""
    _rif = (_rf.group(1).strip() if _rf else "").strip()
    if _rif.lower() in ("nessuno", "nessun", "n/a", "-", ""):
        _rif = ""
    if 1 <= _n <= len(candidati):
        return {"indice": _n - 1, "motivo": _motivo, "riferimento": _rif,
                "errore": None}
    # nessun candidato valido: l'IA propone un altro versetto
    if _rif:
        return {"indice": None, "motivo": _motivo, "riferimento": _rif,
                "errore": None}
    return {"indice": None, "motivo": _motivo, "riferimento": "",
            "errore": "IA non ha scelto un versetto valido"}


def _chiedi_ia_testo(prompt: str, chiave_gemini: str = "",
                     chiave_openai: str = "") -> str:
    """Chiede un testo semplice all'IA migliore disponibile."""
    if chiave_gemini or chiave_gemini_da_secrets():
        for m in MODELLI_GEMINI:
            _t = _gemini_con_sdk(prompt, chiave_gemini or
                                 chiave_gemini_da_secrets(), m, 90)
            if len(_t) > 5:
                return _t
    _r = interpreta_gratis(prompt, tentativi=1)
    if _r.get("testo"):
        return _r["testo"]
    if chiave_openai:
        _r = interpreta_con_ia(prompt, chiave=chiave_openai)
        if _r.get("testo"):
            return _r["testo"]
    return ""


def _pulisci_giornale(testo: str) -> str:
    """
    Se la risposta e' stata troncata a meta' frase, la riporta all'ultima
    frase completa (meglio una risposta un po' piu' corta che una parola
    mozzata).
    """
    t = (testo or "").strip()
    if not t:
        return t
    # se finisce con un carattere di punteggiatura, e' completa
    if t[-1] in ".!?;:)\"'":
        return t
    # cerco l'ultimo punto/virgola "forte" e taglio li'
    for sep in (". ", ".\n", "! ", "? "):
        idx = t.rfind(sep)
        if idx > len(t) * 0.4:
            return t[:idx + 1].strip()
    # niente: taglio all'ultima newline
    idx = t.rfind("\n")
    if idx > len(t) * 0.4:
        return t[:idx].strip()
    return t


def interpreta_gratis(prompt: str, timeout: int = 120,
                      tentativi: int = 3) -> dict:
    """
    Chiede l'interpretazione a una IA GRATUITA che non richiede chiave API.

    Restituisce: {"testo": ..., "parole_chiave": [...], "errore": None|str,
                  "modello": ..., "fonte": ...}
    Non solleva mai: se fallisce, l'errore torna nel dizionario e l'app
    ripiega sul motore di studio (che funziona sempre).
    """
    vuoto = {"testo": "", "parole_chiave": [], "modello": "",
             "fonte": "IA gratuita"}
    if requests is None:
        return {**vuoto, "errore": "requests non installato"}

    import time

    ultimo_errore = ""
    for tentativo in range(max(1, tentativi)):
        try:
            risposta = requests.post(
                URL_POLLINATIONS,
                json={
                    "model": MODELLO_POLLINATIONS,
                    "messages": [
                        {"role": "system", "content": SISTEMA_BREVE},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 4000,
                    "stream": False,
                },
                timeout=timeout,
                headers={"User-Agent": "Mozilla/5.0 (compatible; CANTICO/1.0)"},
            )
            if risposta.status_code == 200:
                testo = _estrai_testo_ia(risposta.text or "")
                if len(testo) > 120:
                    return {
                        "testo": testo,
                        "parole_chiave": [],
                        "errore": None,
                        "modello": MODELLO_POLLINATIONS,
                        "fonte": "IA gratuita (Pollinations)",
                    }
                ultimo_errore = "risposta non utilizzabile"
            elif risposta.status_code == 402:
                ultimo_errore = ("servizio gratuito troppo richiesto "
                                 "(attendo e riprovo)")
            else:
                ultimo_errore = (f"errore {risposta.status_code}: "
                                 f"{risposta.text[:120]}")
        except Exception as exc:
            ultimo_errore = f"IA non raggiungibile: {exc}"

        if tentativo < tentativi - 1:
            time.sleep(32)   # il limite e' 1 risposta ogni 30 secondi

    return {**vuoto, "errore": ultimo_errore or "IA gratuita non disponibile"}
