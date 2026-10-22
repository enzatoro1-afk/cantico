# -*- coding: utf-8 -*-
"""
imposta_chiavi_cloud.py
=======================
Porta le chiavi che hai nel file LOCALE `.streamlit/secrets.toml` nei
"Secrets" dell'app su Streamlit Community Cloud.

Perche' serve:
    il file `.streamlit/secrets.toml` e' in `.gitignore` (e deve restarlo:
    contiene le chiavi). Percio' NON viene caricato su GitHub e NON arriva
    all'app online: li' la chiave Gemini non c'e' e l'app cade sulla IA
    gratuita, che e' lentissima.
    Questo script copia le chiavi nei Secrets del Cloud (via API officiale),
    senza mostrarle e senza scriverle in GitHub.

Uso:
    python imposta_chiavi_cloud.py                    # chiede il token
    python imposta_chiavi_cloud.py --token "XXX"      # token come argomento
    python imposta_chiavi_cloud.py --controlla        # solo verifica
    $env:STREAMLIT_TOKEN="XXX"; python imposta_chiavi_cloud.py

Il token si crea qui (gratis, 1 minuto):
    https://share.streamlit.io/account/settings  ->  "API tokens" -> Create

Nessuna chiave viene stampata: lo script mostra solo i NOMI dei segreti.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


class _Risposta:
    """Risposta minima, come quella di requests."""

    def __init__(self, status: int, testo: str):
        self.status_code = status
        self.text = testo

    def json(self):
        return json.loads(self.text or "{}")


def _richiesta(metodo: str, url: str, token: str, corpo=None,
                timeout: int = 60) -> _Risposta:
    """Chiamata HTTP con la libreria standard (niente 'requests' richiesto)."""
    _dati = None
    _headers = {"Authorization": f"Bearer {token}",
                "User-Agent": "CANTICO/1.0"}
    if corpo is not None:
        _dati = json.dumps(corpo).encode("utf-8")
        _headers["Content-Type"] = "application/json"
    _req = urllib.request.Request(url, data=_dati, headers=_headers,
                                 method=metodo)
    try:
        with urllib.request.urlopen(_req, timeout=timeout) as _r:
            return _Risposta(_r.status, _r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as _e:
        return _Risposta(_e.code, _e.read().decode("utf-8", "replace"))
    except Exception as _e:
        return _Risposta(0, str(_e))

PROG = r"C:\Users\toroe\OneDrive\Documenti\Progetto predefinito\Assistente-Canzone-TikTok"
API = "https://api.streamlit.io/v1"
FILE_SECRETS = os.path.join(PROG, ".streamlit", "secrets.toml")

# le chiavi da caricare: nome nel file -> nome nel Cloud
CHIAVI = {
    "GEMINI_API_KEY": "GEMINI_API_KEY",
    "GOOGLE_API_KEY": "GOOGLE_API_KEY",
    "TREBLO_API_KEY": "TREBLO_API_KEY",
    "HF_TOKEN": "HF_TOKEN",
    "OPENAI_API_KEY": "OPENAI_API_KEY",
    "APP_PASSWORD_SHA256": "APP_PASSWORD_SHA256",
}


def _ok(msg: str) -> None:
    print("  [OK] " + msg)


def _err(msg: str) -> None:
    print("  [!] " + msg)


def leggi_secrets_locale() -> dict:
    """Legge le chiavi dal file .streamlit/secrets.toml (senza stamparle)."""
    if not os.path.exists(FILE_SECRETS):
        print(f"Non trovo {FILE_SECRETS}")
        return {}
    try:
        import tomllib
        with open(FILE_SECRETS, "rb") as f:
            return dict(tomllib.load(f) or {})
    except Exception as exc:
        print("Non riesco a leggere il file dei secrets:", exc)
        return {}


def chiedi_token(argomento: str = "") -> str:
    if argomento:
        return argomento.strip()
    _t = (os.environ.get("STREAMLIT_TOKEN", "") or "").strip()
    if _t:
        return _t
    print("\nServe il TOKEN API di Streamlit (lo trovi qui:)")
    print("   https://share.streamlit.io/account/settings  ->  API tokens"
          "  ->  Create")
    print("Incollalo qui (non lo mostro mentre lo scrivi):")
    try:
        import getpass
        return getpass.getpass("Token: ").strip()
    except Exception:
        return input("Token: ").strip()


def trova_app(token: str, nome: str = "") -> dict:
    """Elenco delle app del workspace e ricerca di quella giusta."""
    _r = _richiesta("GET", f"{API}/apps", token)
    if _r.status_code != 200:
        _err(f"Non riesco a leggere le app ({_r.status_code}): {_r.text[:200]}")
        return {}
    _d = _r.json() or {}
    _apps = _d.get("apps") or []
    if not _apps:
        _err("Non vedo nessuna app in questo workspace.")
        return {}
    print(f"\nLe app nel tuo workspace ({len(_apps)}):")
    for _a in _apps:
        print(f"   - {_a.get('name')}  [{_a.get('status')}]  {_a.get('url')}")
    for _a in _apps:
        _url = (_a.get("url") or "")
        _n = (_a.get("name") or "")
        if nome and (nome.lower() in _n.lower() or nome.lower() in _url.lower()):
            return _a
    for _a in _apps:
        if "canzoni" in (_a.get("name") or "").lower() or \
           "canzoni" in (_a.get("url") or "").lower():
            return _a
    return _apps[0]


def segreti_attuali(token: str, app_id: str) -> list:
    _r = _richiesta("GET", f"{API}/apps/{app_id}/secrets", token)
    if _r.status_code != 200:
        return []
    try:
        return ((_r.json() or {}).get("secrets") or [])
    except Exception:
        return []


def scrivi_secrets(token: str, app_id: str, toml_testo: str) -> bool:
    _r = _richiesta("PUT", f"{API}/apps/{app_id}/secrets", token,
                    {"secrets": toml_testo}, timeout=90)
    if _r.status_code == 200:
        return True
    _err(f"Salvataggio fallito ({_r.status_code}): {_r.text[:300]}")
    return False


def _toml_da_dati(dati: dict) -> str:
    _righe = []
    for _k, _v in dati.items():
        _righe.append(f'{_k} = "{_v}"')
    return "\n".join(_righe) + "\n"


def main() -> int:
    _ap = argparse.ArgumentParser(description="Porta le chiavi locali nei "
                                             "Secrets di Streamlit Cloud")
    _ap.add_argument("--token", default="", help="token API di Streamlit")
    _ap.add_argument("--app", default="", help="nome (o URL) dell'app")
    _ap.add_argument("--controlla", action="store_true",
                     help="solo verifica: non scrive niente")
    _ap.add_argument("--senza", default="",
                     help="chiavi da NON caricare (separate da virgola). "
                          "Es. --senza GEMINI_API_KEY: l'app resta senza "
                          "Gemini sul server e ognuno mette la sua nel "
                          "browser (la quota resta a ciascuno).")
    _ap.add_argument("--solo", default="",
                     help="carica SOLO queste chiavi (separate da virgola)")
    _args = _ap.parse_args()

    print("=" * 66)
    print(" CANTICO - chiavi su Streamlit Cloud")
    print("=" * 66)

    _locali = leggi_secrets_locale()
    if not _locali:
        _err("Nessuna chiave locale da caricare.")
        return 1
    print("\nChiavi trovate nel file locale (NON vengono mostrate):")
    for _k in CHIAVI:
        if _locali.get(_k):
            print(f"   - {_k}")

    _token = chiedi_token(_args.token)
    if not _token:
        _err("Token mancante: nothing to do.")
        return 1

    _app = trova_app(_token, _args.app)
    if not _app:
        return 1
    _app_id = _app.get("id")
    print(f"\nApp scelta: {_app.get('name')} (id {_app_id})")

    print("\nSecrets ATTUALI sul Cloud:")
    _attuali = segreti_attuali(_token, _app_id)
    if _attuali:
        for _s in _attuali:
            print(f"   - {_s}")
    else:
        print("   (nessuno)")

    if _args.controlla:
        _mancanti = [k for k in CHIAVI if _locali.get(k) and k not in _attuali]
        if _mancanti:
            print("\nMANCANO sul Cloud: " + ", ".join(_mancanti))
        else:
            print("\nTutto gia' al posto suo.")
        return 0

    # le chiavi da caricare (solo quelle riconosciute)
    _da_scrivere = {}
    for _k, _v in _locali.items():
        if _k in CHIAVI.values() and _v:
            _da_scrivere[_k] = str(_v)

    # --senza / --solo
    _senza = {x.strip().upper() for x in _args.senza.split(",") if x.strip()}
    _solo = {x.strip().upper() for x in _args.solo.split(",") if x.strip()}
    if _senza:
        for _k in list(_da_scrivere):
            if _k.upper() in _senza:
                del _da_scrivere[_k]
        print(f"\nEscludo: {', '.join(sorted(_senza))}")
    if _solo:
        for _k in list(_da_scrivere):
            if _k.upper() not in _solo:
                del _da_scrivere[_k]
        print(f"Carico solo: {', '.join(sorted(_solo))}")

    if not _da_scrivere:
        print("\nNessuna chiave da caricare: i Secrets del Cloud restano "
              "come sono.")
        return 0

    print("\nCarico i secrets nel Cloud (l'app si riavvia da sola)...")
    print("   (ATTENZIONE: la API sostituisce TUTTI i secrets: una chiave "
          "che era sul Cloud e non e' in elenco viene rimossa)")
    if not scrivi_secrets(_token, _app_id, _toml_da_dati(_da_scrivere)):
        return 1

    print("\nFatto. Attendi 1-2 minuti che l'app si riavvii, poi apri:")
    print("   " + (_app.get("url") or ""))
    if "GEMINI_API_KEY" not in _da_scrivere:
        print("\nGemini NON e' nei Secrets: e' quello che vuoi se ognuno "
              "deve usare la SUA chiave (la quota resta a ciascuno).")
    print("Nella barra laterale deve comparire: "
          "\u2705 Gemini e' gia' attivo")
    return 0


if __name__ == "__main__":
    sys.exit(main())
