# -*- coding: utf-8 -*-
"""
testi_canzone.py
================
Il testo della canzone: lo scrive l'IA, come un songwriter di lode.

Formato: tag di struttura [Verse], [Chorus], [Bridge] cosi' il motore
musicale li canta bene.
"""

from __future__ import annotations

import re

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore

PROMPT_TESTI = """Sei un songwriter di musica di lode evangelica pentecostale.
Scrivi il TESTO di una canzone (in italiano) basata sul versetto biblico qui sotto.

RIFERIMENTO: {riferimento}
TESTO BIBLICO: {testo_versetto}
SPIRITO DEL TESTO (interpretazione): {interpretazione}
TEMI: {temi}

REGOLE:
- Parti SEMPRE e SOLO dal versetto: il testo della canzone deve parlare di
  quello, senza aggiungere fatti, nomi o storie che non ci sono.
- Non citare altri versetti biblici (niente numeri tipo "Salmo 23:1" dentro il
  testo), solo il significato.
- Usa parole semplici, cantabili, con un ritmo che si possa ripetere.
- Il brano deve stare tra 30 e 60 secondi: 2 strofe, un ritornello, e se
  serve un ponte. NON scrivere piu' di 3 strofe.
- Non nominare artisti, cori, chiese o canzoni esistenti.

Scrivi SOLO il testo, iniziando dalla riga [Verse 1], senza preamboli e senza
spiegazioni. [Chorus] e [Bridge]."""

ESEMPIO = """[Verse 1]
O Eterno, il mio pastore
Niente mi mancherà
Mi guidi per le acque calme
Nella valle camminerò

[Chorus]
Tu sei la mia vita
Il mio riposo sei
Niente mi mancherà
Con Te canterò

[Verse 2]
Mi fai riposare in prato
Tu mi pasci con il tuo amore
..."""


def _prompt(versetto: str, interpretazione: str, temi: str = "",
            lingua: str = "italiano") -> str:
    return PROMPT_TESTI.format(
        riferimento=versetto,
        testo_versetto=interpretazione or "",
        interpretazione=interpretazione or "",
        temi=temi or "fede, lode, speranza",
    )


def scrivi_testi_canzone(versetto: str, interpretazione: str, temi: str = "",
                         chiave_gemini: str = "", chiave_openai: str = "",
                         timeout: int = 120) -> dict:
    """
    Scrive il testo della canzone con l'IA.

    Restituisce {"ok": True, "testo": "..."} oppure {"ok": False, "errore": "..."}
    """
    vuoto = {"ok": False, "errore": "", "testo": ""}
    if requests is None:
        return {**vuoto, "errore": "requests non installato"}

    prompt = _prompt(versetto, interpretazione, temi)
    testo = ""

    # 1) Gemini (se c'e' la chiave)
    if chiave_gemini:
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=chiave_gemini)
            risp = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=(
                        "Sei un songwriter di musica di lode evangelica "
                        "pentecostale. Rispondi SOLO con il testo della "
                        "canzone, in italiano, con i tag [Verse]/[Chorus]."),
                    temperature=0.7, max_output_tokens=1200),
            )
            testo = (risp.text or "").strip()
        except Exception:
            testo = ""

    # 2) IA gratuita senza chiave
    if not testo:
        try:
            from ai_client import interpreta_gratis
            r = interpreta_gratis(prompt, timeout=timeout, tentativi=2)
            testo = (r.get("testo") or "").strip()
        except Exception:
            testo = ""

    # 2b) AIMLAPI (stessa chiave che genera la musica): un modello di testo
    #     scrive le parole, cosi' serve UNA sola chiave per tutto
    if not testo:
        testo = _testi_con_aimlapi(prompt, timeout=timeout)

    # 3) ChatGPT API
    if not testo and chiave_openai:
        try:
            from ai_client import interpreta_con_ia
            r = interpreta_con_ia(prompt, chiave=chiave_openai, timeout=timeout)
            testo = (r.get("testo") or "").strip()
        except Exception:
            testo = ""

    testo = _puliscitesto(testo)
    if not testo:
        return {**vuoto, "errore": (
            "Non sono riuscito a scrivere il testo della canzone. "
            "Controlla la connessione o prova a scriverlo a mano.")}

    if not (("[Verse" in testo) or ("[Verse" in testo)):
        testo = "[Verse 1]\n" + testo

    return {"ok": True, "errore": "", "testo": testo}


def _testi_con_aimlapi(prompt: str, timeout: int = 120) -> str:
    """
    Scrive i testi usando un modello di testo su AIMLAPI (la stessa chiave
    che genera la musica). Serve cosi' una SOLA chiave per tutto.
    """
    try:
        import requests
    except ImportError:
        return ""
    chiave = ""
    for nome in ("AIMLAPI_KEY", "AIML_API_KEY"):
        try:
            import os
            v = (os.environ.get(nome, "") or "").strip()
            if v:
                chiave = v
                break
        except Exception:
            pass
    if not chiave:
        try:
            import tomllib
            import os
            p = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             ".streamlit", "secrets.toml")
            if os.path.exists(p):
                with open(p, "rb") as f:
                    d = tomllib.load(f)
                for nome in ("AIMLAPI_KEY", "AIML_API_KEY"):
                    v = str(d.get(nome, "") or "").strip()
                    if v:
                        chiave = v
                        break
        except Exception:
            pass
    if not chiave:
        return ""
    try:
        r = requests.post(
            "https://api.aimlapi.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {chiave}",
                     "Content-Type": "application/json"},
            json={"model": "openai/gpt-5-5",
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=timeout)
        if r.status_code != 200:
            return ""
        d = r.json()
        return str((d.get("choices") or [{}])[0]
                   .get("message", {}).get("content", "") or "").strip()
    except Exception:
        return ""


def _puliscitesto(testo: str) -> str:
    """Toglie i preamboli che l'IA aggiunge e lascia solo le righe utili."""
    t = (testo or "").strip()
    if not t:
        return ""
    righe = []
    for r in t.split("\n"):
        r = r.strip()
        if not r:
            continue
        # salta le frasi di spiegazione prima delle tag
        if not righe and not r.startswith("["):
            if re.match(r"^(ecco|certo|sure|here|ok|bene|incluso|testo)", r,
                         re.IGNORECASE) and len(r) < 90:
                continue
        righe.append(r)
    # via eventuali blocchi di codice
    if "```" in "\n".join(righe):
        parti = "\n".join(righe).split("```")
        righe = [x for x in parti[1::2] if x.strip()] or righe
    return "\n".join(righe).strip()
