# -*- coding: utf-8 -*-
"""
prepara_copia_pubblica.py
=========================
Crea una COPIA PUBBLICA dell'app su Streamlit Community Cloud: la stessa
app, ma SENZA le chiavi del proprietario. Chi la apre la configura da
solo (email + password + le sue chiavi API) e la sua copia resta sua.

Perche' due copie:
- **la tua** (questa): gia' configurata, con le tue chiavi nei Secrets.
  Quando condividi il link, chi entra la usa con le SUE chiavi (le mette
  lui in 2 minuti) e la tua quota non viene toccata.
- **la copia pubblica**: l'app "in bianco", per chi vuole partire da
  zero e configurarsi tutto da solo (o per regalare l'app a qualcuno
  senza dargli il link della tua).

Uso:
    python prepara_copia_pubblica.py                    # chiede il token
    python prepara_copia_pubblica.py --token "XXX"
    python prepara_copia_pubblica.py --nome "mia-app-copia"

Il token si crea qui (gratis, 1 minuto):
    https://share.streamlit.io/account/settings  ->  API tokens  ->  Create

La copia parte DALLO STESSO repository GitHub: quindi e' sempre aggiornata
e non contiene nessuna chiave (le chiavi stanno nei Secrets, che sono per
app, non nel codice).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.streamlit.io/v1"
REPO = "enzatoro1-afk/canzoni-tiktok"
BRANCH = "main"
FILE_APP = "app.py"


def _richiesta(metodo: str, url: str, token: str, corpo=None,
                timeout: int = 90):
    _dati = None
    _h = {"Authorization": f"Bearer {token}", "User-Agent": "CANTICO/1.0"}
    if corpo is not None:
        _dati = json.dumps(corpo).encode("utf-8")
        _h["Content-Type"] = "application/json"
    _req = urllib.request.Request(url, data=_dati, headers=_h, method=metodo)
    try:
        with urllib.request.urlopen(_req, timeout=timeout) as _r:
            return _r.status, _r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as _e:
        return _e.code, _e.read().decode("utf-8", "replace")
    except Exception as _e:
        return 0, str(_e)


def chiedi_token(argomento: str = "") -> str:
    if argomento:
        return argomento.strip()
    _t = (os.environ.get("STREAMLIT_TOKEN", "") or "").strip()
    if _t:
        return _t
    print("\nServe il TOKEN API di Streamlit:")
    print("   https://share.streamlit.io/account/settings -> API tokens "
          "-> Create")
    try:
        import getpass
        return getpass.getpass("Token: ").strip()
    except Exception:
        return input("Token: ").strip()


def app_esistenti(token: str) -> list:
    _st, _t = _richiesta("GET", f"{API}/apps", token)
    if _st != 200:
        print(f"  [!] Non riesco a leggere le app ({_st}): {_t[:200]}")
        return []
    try:
        return ((json.loads(_t or "{}") or {}).get("apps") or [])
    except Exception:
        return []


def main() -> int:
    _ap = argparse.ArgumentParser(description="Crea la copia pubblica "
                                             "dell'app su Streamlit Cloud")
    _ap.add_argument("--token", default="")
    _ap.add_argument("--nome", default="", help="nome della copia")
    _ap.add_argument("--elenca", action="store_true",
                     help="mostra solo le app che hai")
    _args = _ap.parse_args()

    print("=" * 66)
    print(" CANTICO - copia pubblica dell'app")
    print("=" * 66)

    _token = chiedi_token(_args.token)
    if not _token:
        print("  [!] Token mancante.")
        return 1

    _apps = app_esistenti(_token)
    print(f"\nLe app nel tuo workspace ({len(_apps)}):")
    for _a in _apps:
        print(f"   - {_a.get('name')}  [{_a.get('status')}]  {_a.get('url')}")

    if _args.elenca:
        return 0

    _nome = (_args.nome or "canzoni-pentecostali-copia").strip()
    for _a in _apps:
        if (_a.get("name") or "") == _nome:
            print(f"\nLa copia '{_nome}' c'e' gia': {_a.get('url')}")
            print("Niente da fare.")
            return 0

    print(f"\nCreo la copia '{_nome}' dal repository {REPO}...")
    print("(nessuna chiave: la copia si configura da sola, utente per utente)")
    _st, _t = _richiesta("POST", f"{API}/apps", _token, {
        "repo": REPO,
        "branch": BRANCH,
        "mainFile": FILE_APP,
        "appName": _nome,
    })
    if _st not in (200, 201):
        print(f"  [!] Creazione fallita ({_st}): {_t[:400]}")
        return 1
    try:
        _d = json.loads(_t or "{}") or {}
    except Exception:
        _d = {}
    print(f"\n  [OK] Copia creata: {_d.get('name', _nome)}")
    print("       " + str(_d.get("url", "")))
    print("\nAttendi 1-2 minuti che si avvii, poi aprila: li' l'app")
    print("chiede a chi entra la SUA email, la SUA password e le SUE chiavi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
