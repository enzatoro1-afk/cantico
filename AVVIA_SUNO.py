# -*- coding: utf-8 -*-
"""
AVVIA IL SERVIZIO SUNO (open source) con i TUOI crediti gratuiti
================================================================
Questo script avvia il ponte open source verso suno.com, usando la
sessione del TUO account (quindi i crediti gratuiti giornalieri).

COME SI USA (dal PC o dal Codespace):
    python AVVIA_SUNO.py
Lo script:
    1) scarica il progetto open source (se non c'e')
    2) controlla che ci sia il cookie (.suno_cookie.txt)
    3) lancia npm install + npm start
    4) verifica che l'API risponda su http://localhost:8000
"""

import os
import shutil
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")

PROG = os.path.dirname(os.path.abspath(__file__))
REPO_SUNO = "https://github.com/gcui-art/suno-api"
CARTELLA = os.path.join(PROG, "suno-api")
FILE_COOKIE = os.path.join(PROG, ".suno_cookie.txt")
PORTA = 8000


def _internet_meno_che_meno():
    try:
        import requests
        r = requests.get(f"http://localhost:{PORTA}/api/v1/health", timeout=6)
        return r.status_code == 200
    except Exception:
        return False


def main():
    print("=" * 70)
    print("SERVIZIO SUNO (crediti gratuiti del tuo account)")
    print("=" * 70)

    if _internet_meno_che_meno():
        print(f"\nIl servizio e' GIA' attivo su http://localhost:{PORTA}.")
        print("Vai nell'app -> 'Crea una canzone ORIGINALE' -> motore Suno.")
        return 0

    # 1) il cookie
    if not os.path.exists(FILE_COOKIE):
        print("\n[1/4] Non trovo il cookie di suno.com.")
        print("      Fai il login su https://suno.com, poi F12 -> Console ->")
        print("      copy(document.cookie) -> Invio, e poi lancia:")
        print("          python SALVA_COOKIE_SUNO.py")
        return 1
    print("\n[1/4] Cookie trovato.")

    # 2) il progetto
    if not os.path.isdir(CARTELLA):
        print("[2/4] Scarico il progetto open source...")
        try:
            subprocess.run(["git", "clone", "--depth", "1", REPO_SUNO, CARTELLA],
                           check=True, timeout=300)
        except Exception as exc:
            print(f"      ERRORE: {exc}")
            return 1
    else:
        print("[2/4] Progetto gia' presente.")

    # 3) npm install
    npm = shutil.which("npm")
    if not npm:
        print("\n[3/4] 'npm' non trovato: installa Node.js (nodejs.org) e riprova.")
        return 1
    print("[3/4] Installo le dipendenze (npm install)...")
    try:
        subprocess.run([npm, "install"], cwd=CARTELLA, check=True, timeout=900)
    except Exception as exc:
        print(f"      ERRORE in npm install: {exc}")
        return 1

    # 4) avvio
    print(f"[4/4] Avvio il servizio su http://localhost:{PORTA} ...")
    print("      (lascia questa finestra APERTA: il servizio deve restare vivo)")
    env = dict(os.environ)
    env["PORT"] = str(PORTA)
    env.setdefault("SUNO_COOKIE", open(FILE_COOKIE, encoding="utf-8").read().strip())
    try:
        proc = subprocess.Popen([npm, "start"], cwd=CARTELLA, env=env)
    except Exception as exc:
        print(f"      ERRORE: {exc}")
        return 1

    print("      Aspetto che l'API risponda...")
    for _ in range(40):
        time.sleep(3)
        if _internet_meno_che_meno():
            print("\n      FATTO! L'API e' attiva su "
                  f"http://localhost:{PORTA}")
            print("      Ora apri l'app -> 'Crea una canzone ORIGINALE' ->")
            print("      motore 'Suno (i tuoi crediti gratuiti)'.")
            print("      (questa finestra deve restare aperta)")
            try:
                proc.wait()
            except KeyboardInterrupt:
                pass
            return 0
    print("      Il servizio non ha risposto entro 2 minuti. "
          "Guarda i messaggi sopra.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
