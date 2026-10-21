# -*- coding: utf-8 -*-
"""
configura.py
============
IL "PRIMO AVVIO" di chi scarica l'app: una finestra che dice esattamente
cosa manca e come sistemarlo, e salva le chiavi nel file locale
`.streamlit/secrets.toml` (che e' in .gitignore: le chiavi non finiscono
MAI su GitHub).

Filosofia: le chiavi le CREA e le INSERISCE chi usa l'app. Nessun'altra
persona (ne' io, ne' il server) le vede o le usa per conto suo.
"""

from __future__ import annotations

import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

# --------------------------------------------------------------------------
# Cosa serve, in ordine di importanza
# --------------------------------------------------------------------------

PASSI = [
    {
        "chiave": "gemini",
        "titolo": "1) Google Gemini - l'interpretazione e i testi",
        "perche": ("Serve per l'interpretazione scritta come un maestro della "
                   "Scrittura e per scrivere il testo del cantico. "
                   "Senza, l'app usa il motore di studio (funziona comunque)."),
        "come": [
            "Apri https://aistudio.google.com/api-keys con il tuo account Google",
            "Clicca 'Create API key' e copia la chiave",
            "Incollala qui sotto e premi 'Salva'",
        ],
        "link": "https://aistudio.google.com/api-keys",
        "esempio": "AIzaSy...",
    },
    {
        "chiave": "aimlapi",
        "titolo": "2) AIMLAPI - (opzionale) per comporre con voce",
        "perche": ("Serve solo se vuoi che l'app componga una canzone cantata "
                   "e ti prepari il video .mp4. Ha un piano a consumo: "
                   "controlla il credito disponibile."),
        "come": [
            "Registrati su https://aimlapi.com",
            "Copia la chiave dalla tua area account",
            "Incollala qui sotto (opzionale)",
        ],
        "link": "https://aimlapi.com",
        "esempio": "f3a9b74d...",
    },
]

ISTRUZIONE_SUNO = """\
Suno: per usare i crediti gratuiti giornalieri del TUO account
(serve un servizio open source che fa da ponte con suno.com):

 1) Nel terminale, dentro la cartella dell'app:
        python AVVIA_SUNO.py
    (il progetto open source viene scaricato e avviato da solo)
 2) Fai il login su https://suno.com, poi F12 -> Console ->
        copy(document.cookie)
    e premi Invio (il cookie va negli appunti)
 3) Torna nel terminale e lancia:
        python SALVA_COOKIE_SUNO.py
    e incolla il cookie. Non passarlo dalla chat: cosi' resta solo
    sul tuo computer (file .suno_cookie.txt, che e' in .gitignore).
 4) Nell'app scegli il motore 'Suno (i tuoi crediti gratuiti)'.
"""

TESTO_SUNO = """\
Questa app ti aiuta a trasformare un versetto in un post per TikTok.
Funziona subito, ma per un risultato migliore puoi aggiungere due chiavi
(sono gratis, e restano solo sul tuo computer).

1) Google Gemini -> l'interpretazione scritta come un maestro della
   Scrittura, e il testo del cantico.
   https://aistudio.google.com/api-keys

2) (facoltativo) La creazione del video .mp4 per TikTok funziona gia'
   senza chiavi: l'app monta il tuo testo sullo sfondo e produce il video.
   Se vuoi anche una canzone CANTATA, serve un motore musicale:
   - Suno con i crediti gratuiti del tuo account (istruzioni sotto)
   - oppure ACE-Step / MusicGen, open source e gratis
"""


def _su_streamlit_cloud() -> bool:
    """True se l'app gira su Streamlit Cloud (container condiviso)."""
    try:
        base = os.path.dirname(os.path.abspath(__file__))
        return (base.startswith("/home/app") or base.startswith("/app/")
                or base.startswith("/app"))
    except Exception:
        return False


def _percorso_secrets() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        ".streamlit", "secrets.toml")


def leggi_secrets() -> dict:
    try:
        import tomllib
        p = _percorso_secrets()
        if os.path.exists(p):
            with open(p, "rb") as f:
                return dict(tomllib.load(f))
    except Exception:
        pass
    return {}


def scrivi_secrets(valori: dict) -> tuple[bool, str]:
    """Scrive (o aggiorna) .streamlit/secrets.toml. Restituisce (ok, messaggio)."""
    try:
        p = _percorso_secrets()
        os.makedirs(os.path.dirname(p), exist_ok=True)
        # le chiavi gia' presenti vengono SOSTITUITE, non duplicate
        attuali = leggi_secrets()
        attuali.update({k: v for k, v in valori.items()
                         if str(v or "").strip()})
        # conserva i commenti iniziali
        commenti = ["# Configurazione locale (mai su GitHub: .gitignore lo esclude)"]
        try:
            with open(p, "r", encoding="utf-8") as f:
                for r in f.read().split("\n"):
                    if r.strip().startswith("#") and "Configurazione" not in r:
                        commenti.append(r)
        except Exception:
            pass
        righe = list(commenti)
        for k, v in attuali.items():
            righe.append(f'{k} = "{v}"')
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(righe) + "\n")
        return True, f"Salvato in {os.path.basename(p)}"
    except Exception as exc:
        return False, f"Non sono riuscito a salvare: {exc}"


def stato_configurazione() -> dict:
    """Cosa c'e' gia' e cosa manca."""
    s = leggi_secrets()
    out = {}
    for passo in PASSI:
        k = passo["chiave"]
        nome = "GEMINI_API_KEY" if k == "gemini" else "AIMLAPI_KEY"
        out[k] = bool(str(s.get(nome, "") or "").strip())
    # il cookie Suno
    try:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         ".suno_cookie.txt")
        out["suno"] = os.path.exists(p) and os.path.getsize(p) > 20
    except Exception:
        out["suno"] = False
    out["cloud"] = _su_streamlit_cloud()
    return out
