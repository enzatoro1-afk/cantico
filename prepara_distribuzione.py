# -*- coding: utf-8 -*-
"""
prepara_distribuzione.py
========================
Prepara la cartella da mandare a qualcun altro: l'app COMPLETA, ma
"in bianco" — cioe' SENZA le tue chiavi, senza i tuoi post, senza i tuoi
cookie. Chi la riceve:

1. apre l'app e **imposta la sua password** (l'app glielo chiede);
2. mette **la sua email** e **le sue chiavi API** nel pannello
   "Configura la tua app" (2 minuti, tutto guidato);
3. da quel momento **l'app e' sua**: i suoi post, la sua quota, la sua
   password. Le tue risorse non vengono toccate.

Uso:
    python prepara_distribuzione.py            # crea la cartella
    python prepara_distribuzione.py --zip      # crea anche lo ZIP
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import zipfile

PROG = os.path.dirname(os.path.abspath(__file__))
DEST = os.path.join(PROG, "DISTRIBUZIONE")

# cosa NON finisce nella cartella (e perché)
ESCLUSI = {
    ".venv", "venv", "__pycache__", ".git", "DISTRIBUZIONE",
    "secrets.toml", "SEGRETS-CLOUD.txt", "link.txt",
    ".chiave_gemini_server.json", ".chiave_treblo_server.json",
    ".chiave_hf_server.json", ".suno_cookie.txt",
    "imposta_chiavi_cloud.py",     # strumento del proprietario
    "prepara_copia_pubblica.py",   # strumento del proprietario
    "prepara_distribuzione.py",    # questo file
    "pubblica.py",                 # push del proprietario
    "CANTICO-app.zip",
}

# file che vengono creati "puliti" invece di essere copiati
ACCESSO_VUOTO = '''# -*- coding: utf-8 -*-
"""
accesso.py
==========
La password di accesso alla TUA app.

Qui non c'e' nessuna password: quando apri l'app te la chiede e te la fai
scegliere tu. Da quel momento la password e' nel TUO browser (come hash
SHA-256, mai in chiaro) e l'app e' solo tua.

Se vuoi cambiarla, cambia la riga qui sotto con l'hash di quella nuova:
    python -c "import hashlib;print(hashlib.sha256('NUA-PASSWORD'.encode()).hexdigest())"
"""

PASSWORD_SHA256 = ""
'''

LEGGIMI = """CANTICO - dalla Parola alla Lode
==============================

Questa e' la TUA app: tutto quello che le dai e' tuo, e non ci metti
niente dentro. Nella tua copia non c'e' la chiave di nessun altro.

COME SI USA (2 minuti, una volta sola)
--------------------------------------
1) APRI L'APP
   - dal computer: apri "AVVIA.ps1" con un doppio clic (si avvia da sola)
   - dal telefono: apri l'app dal link che ti hanno dato
2) IMPOSTA LA PASSWORD DELLA TUA APP
   - te la chiede lei: scegline una (6 caratteri) e ricordala
3) CONFIGURA LE TUE CHIAVI
   - in alto a sinistra trovi "Configura la tua app":
     passo 1: la tua email e la password (quella che hai appena scelto)
     passo 2: per ogni servizio apri la pagina ufficiale, crea la chiave,
              torni qui e premi "Incolla" (la mette da sola) e poi "Verifica"
     passo 3: "Salva la mia app"
   - le chiavi sono GRATIS (Gemini, Treblo, Hugging Face) e restano nel
     TUO browser: nessun altro le vede e la quota e' tutta tua

DOPO, Ogni VOLTA CHE APRI L'APP
-------------------------------
- scrivi un versetto (o un tuo pensiero) nella casella
- "Trova il testo adatto" -> l'app cerca il versetto che ti parla
- "Studia questo passaggio" -> l'interpretazione + la riflessione + il post
  gia' pronti (testo a schermo, script da dire, caption, momento giusto)
- scegli la canzone -> copi e pubblichi su TikTok

LE TUE COSE SONO TUE
-------------------
- i tuoi post restano nel tuo browser: nessun altro li vede
- se un giorno vuoi liberare spazio: in fondo c'e' "Cancella i miei dati"
- la password dell'app e' nel tuo browser (mai in chiaro)

PER CHI VOLESSE UN GIORNO PUBBLICARLA ONLINE
---------------------------------------------
- con "INSTALLA.ps1" (doppio clic) si pubblica gratis su Streamlit Cloud
- con "CARICA.ps1" si carica su GitHub
- i due comandi chiedono solo il tuo username GitHub e un token
"""


def _copia(pub: list[str]) -> None:
    for _n in pub:
        _s = os.path.join(PROG, _n)
        _d = os.path.join(DEST, _n)
        if os.path.isdir(_s):
            shutil.copytree(_s, _d, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns(*ESCLUSI))
        else:
            shutil.copy2(_s, _d)


def main() -> int:
    _ap = argparse.ArgumentParser(description="Prepara la cartella da mandare")
    _ap.add_argument("--zip", action="store_true", help="crea anche lo ZIP")
    _args = _ap.parse_args()

    print("=" * 66)
    print(" CANTICO - preparo la cartella da distribuire")
    print("=" * 66)

    if os.path.exists(DEST):
        shutil.rmtree(DEST, ignore_errors=True)
    os.makedirs(DEST, exist_ok=True)

    # tutto il codice, pulito
    _pub = []
    for _n in sorted(os.listdir(PROG)):
        if _n in ESCLUSI or _n.startswith(".") or _n.startswith("archivio_") \
                or _n.startswith("PROVA_"):
            continue
        if _n.endswith((".zip", ".mp4", ".m4a", ".wav", ".webm")):
            continue
        _pub.append(_n)
    _copia(_pub)

    # la cartella .streamlit: solo config.toml, MAI secrets.toml
    _st = os.path.join(DEST, ".streamlit")
    os.makedirs(_st, exist_ok=True)
    _cfg = os.path.join(PROG, ".streamlit", "config.toml")
    if os.path.exists(_cfg):
        shutil.copy2(_cfg, os.path.join(_st, "config.toml"))

    # accesso.py SENZA password: chi apre la imposta
    with open(os.path.join(DEST, "accesso.py"), "w", encoding="utf-8") as f:
        f.write(ACCESSO_VUOTO)

    # le istruzioni per chi riceve
    with open(os.path.join(DEST, "LEGGIMI.txt"), "w", encoding="utf-8") as f:
        f.write(LEGGIMI)

    # controllo di sicurezza: nessuna chiave, nessun dato personale
    _problemi = []
    for _radice, _dirs, _files in os.walk(DEST):
        for _f in _files:
            _p = os.path.join(_radice, _f)
            _n = os.path.basename(_p)
            if _n in ("secrets.toml", "SEGRETS-CLOUD.txt") or \
                    _n.startswith(".chiave_") or _n == ".suno_cookie.txt" or \
                    _n.startswith("archivio_"):
                _problemi.append(_p)
            if _n == "accesso.py":
                _t = open(_p, encoding="utf-8").read()
                if 'PASSWORD_SHA256 = ""' not in _t:
                    _problemi.append(_p + " (password non vuota!)")
    if _problemi:
        print("\n  [!] ATTENZIONE, ci sono file che non dovevano esserci:")
        for _p in _problemi:
            print("      " + _p)
        return 1

    _n_file = sum(len(_f) for _, _, _f in os.walk(DEST))
    print(f"\n  [OK] Cartella pronta: {DEST}")
    print(f"       {_n_file} file, nessuna chiave, nessun dato personale")
    print("       accesso.py senza password: chi apre la imposta")

    if _args.zip:
        _zip = os.path.join(PROG, "CANTICO-app.zip")
        if os.path.exists(_zip):
            os.remove(_zip)
        with zipfile.ZipFile(_zip, "w", zipfile.ZIP_DEFLATED) as _z:
            for _radice, _dirs, _files in os.walk(DEST):
                for _f in _files:
                    _p = os.path.join(_radice, _f)
                    _z.write(_p, os.path.relpath(_p, DEST))
        print(f"  [OK] ZIP pronto: {_zip}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
