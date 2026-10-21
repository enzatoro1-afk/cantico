# -*- coding: utf-8 -*-
"""
SALVA IL COOKIE DI SUNO (senza passarlo dalla chat)
=====================================================
ISTRUZIONI:
 1) apri suno.com nel browser e fai il login
 2) F12 -> Console (o "DevTools") -> scrivi:
        copy(document.cookie)
    e premi Invio (il cookie va negli appunti)
 3) apri questo file con il Blocco Note e incolla il cookie qui
    (questo file NON e' mai su GitHub: e' in .gitignore)

Poi lancia il servizio open source (in una cartella a parte):
    git clone https://github.com/gcui-art/suno-api
    cd suno-api
    npm install
    npm start
e l'app lo trova su http://localhost:8000
"""

import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

PROG = os.path.dirname(os.path.abspath(__file__))
DEST = os.path.join(PROG, ".suno_cookie.txt")

print("=" * 70)
print("Salva il cookie di suno.com")
print("=" * 70)
print("1) fai il login su https://suno.com")
print("2) F12 -> Console -> copy(document.cookie) -> Invio")
print("3) incolla qui sotto e premi Invio")
print()

try:
    cookie = input("Cookie (invio per confermare): ").strip()
except EOFError:
    print("\nChiuso senza salvare.")
    sys.exit(1)

if not cookie:
    print("Nessun cookie: non ho salvato niente.")
    sys.exit(1)

if "\n" in cookie:
    cookie = cookie.splitlines()[0].strip()

with open(DEST, "w", encoding="utf-8", newline="\n") as f:
    f.write(cookie)

print(f"\nFatto: cookie salvato in {os.path.basename(DEST)} "
      f"({len(cookie)} caratteri)")
print("Ora lancia il servizio open source e usa il motore 'Suno' nell'app.")
