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
]

ISTRUZIONE_TREBLO = """\
Treblo: il motore che CANTA il tuo testo e ti lascia scaricare l'audio
(quindi il video .mp4 si fa tutto da solo, senza passaggi manuali).

Serve UNA cosa sola: la tua chiave API di Treblo (gratis).

 1) Crea l'account su https://treblo.com (puoi entrare con Google)
 2) Vai su https://treblo.com/developers/account e crea una chiave API
 3) Incollala nella barra laterale dell'app, campo "Chiave Treblo"
    (campo "Chiave Treblo (facoltativa, gratis)")

Con l'account nuovo hai 3.000 crediti gratis = 30 canzoni.
Ogni canzone costa 100 crediti. La chiave resta nel tuo browser:
non passa dalla chat e non finisce su GitHub.
"""

ISTRUZIONE_SUNO = """\
Suno: per usare i crediti gratuiti giornalieri del TUO account.

Serve UNA cosa sola: il tuo cookie di suno.com. Non devi installare
niente (niente Node, niente servizi): l'app parla con Suno esattamente
come fa la pagina web di Suno.

 1) Fai il login su https://suno.com
 2) F12 -> scheda "Network" (Rete) -> ricarica la pagina (F5)
    -> clicca una richiesta -> in "Request Headers" copia la riga
    "cookie" (inizia con __client=... oppure __session=...)
 3) Salvalo sul tuo computer (il cookie NON passa dalla chat e NON
    finisce su GitHub):
         python AGGIORNA_COOKIE_SUNO.py
    e incolla il valore.
 4) Nell'app scegli il motore 'Suno (i tuoi crediti gratuiti)'.

Il cookie vale circa un'ora: quando scade, l'app te lo dice e basta
rinnovarlo con lo stesso comando.
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
        nome = "GEMINI_API_KEY"
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
