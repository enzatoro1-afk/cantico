# -*- coding: utf-8 -*-
"""
AGGIORNA_COOKIE_SUNO.py
=======================
Mette il cookie di suno.com nei posti giusti, senza passarlo dalla chat.

Come si usa (dal PC, senza aprire la chat):

    python AGGIORNA_COOKIE_SUNO.py

Il programma chiede di incollare il cookie (F12 -> Network -> una richiesta ->
Request Headers -> riga "cookie") e lo scrive:

  - ./.suno_cookie.txt      (quello che legge l'app, in .gitignore)
  - ~/suno-api/.env         (quello che legge il servizio open source)

Niente va su GitHub e niente passa dalla chat.
"""

from __future__ import annotations

import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

PROG = os.path.dirname(os.path.abspath(__file__))
FILE_COOKIE = os.path.join(PROG, ".suno_cookie.txt")
FILE_ENV = os.path.join(os.path.expanduser("~"), "suno-api", ".env")

ISTRUZIONI = """
Dov'è il cookie di suno.com:

  1) Apri https://suno.com (e fai il login)
  2) Premi F12 -> scheda "Network" (Rete) -> ricarica la pagina (F5)
  3) Clicca la prima richiesta della lista
  4) In "Request Headers" cerca la riga "cookie:" e copia TUTTO il valore
     (inizia con __client=... oppure __session=...)
  5) Torna qui e incolla il valore, poi premi Invio.

Il cookie resta sul tuo computer: non passa dalla chat e non finisce
su GitHub.
"""


def _scrivi(cookie: str) -> bool:
    cookie = (cookie or "").strip()
    if len(cookie) < 20 or "=" not in cookie:
        print("Il cookie sembra incompleto. Riprova.")
        return False
    try:
        with open(FILE_COOKIE, "w", encoding="utf-8", newline="\n") as f:
            f.write(cookie)
    except Exception as exc:
        print(f"Non sono riuscito a scrivere {FILE_COOKIE}: {exc}")
        return False
    try:
        os.makedirs(os.path.dirname(FILE_ENV), exist_ok=True)
        with open(FILE_ENV, "w", encoding="utf-8", newline="\n") as f:
            f.write(f"SUNO_COOKIE={cookie}\n")
            f.write("BROWSER=chromium\nBROWSER_HEADLESS=true\n"
                    "BROWSER_LOCALE=en\n")
    except Exception as exc:
        print(f"Non sono riuscito a scrivere {FILE_ENV}: {exc}")
    print(f"Cookie salvato ({len(cookie)} caratteri):")
    print(f"  - {FILE_COOKIE}")
    print(f"  - {FILE_ENV}")
    ha = [n for n in ("__client=", "__session=") if n in cookie]
    print(f"  cookie presenti: {', '.join(ha) if ha else 'nessuno utile'}")
    return True


def _da_file() -> str:
    """Se c'è un file con il cookie (per esempio scaricato dal browser)."""
    for nome in ("suno_cookie.txt", "suno_cookie_full.txt"):
        p = os.path.join(os.path.expanduser("~"), "Downloads", nome)
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return f.read().strip()
            except Exception:
                continue
    return ""


def main() -> int:
    print(ISTRUZIONI)
    da_file = _da_file()
    if da_file:
        print("Ho trovato un cookie scaricato. Lo uso? (s/n)", end=" ")
        if (input().strip().lower() or "s") == "s":
            return 0 if _scrivi(da_file) else 1
    print("Incolla qui il cookie e premi Invio (Ctrl+C per annullare):")
    try:
        cookie = input().strip()
    except (KeyboardInterrupt, EOFError):
        print("\nAnnullato.")
        return 1
    return 0 if _scrivi(cookie) else 1


if __name__ == "__main__":
    sys.exit(main())
