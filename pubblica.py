# -*- coding: utf-8 -*-
"""
pubblica.py - push automatico con VERSION.txt
==============================================
Fa: commit -> scrive VERSION.txt con il commit -> commit del VERSION
-> push. Cosi' l'app online mostra sempre 'versione <sha> <data>' e si
sa subito se gira il codice giusto.

Uso:  python pubblica.py "messaggio del commit"
"""

import os
import subprocess
import sys

PROG = r"C:\Users\toroe\OneDrive\Documenti\Progetto predefinito\Assistente-Canzone-TikTok"
GIT = r"C:\Program Files\Git\cmd\git.exe"
REPO = "https://github.com/enzatoro1-afk/canzoni-tiktok.git"


def git(*args, **kw):
    return subprocess.run([GIT, *args], cwd=PROG, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", **kw)


def main():
    msg = sys.argv[1] if len(sys.argv) > 1 else "aggiornamento"
    os.chdir(PROG)

    # 1) commit di tutto
    git("add", "-A")
    r = git("commit", "-m", msg)
    print("commit:", (r.stdout or r.stderr).strip().splitlines()[0][:120])

    # 2) sha del commit appena creato
    sha = git("rev-parse", "HEAD").stdout.strip()[:7]
    data = git("log", "-1", "--format=%cd", "--date=format:%Y-%m-%d %H:%M").stdout.strip()
    print("sha:", sha, "| data:", data)

    # 3) VERSION.txt con lo sha
    with open(os.path.join(PROG, "VERSION.txt"), "w", encoding="utf-8") as f:
        f.write(f"build {sha} · {data}\n")

    # 4) commit + push
    git("add", "VERSION.txt")
    git("commit", "-m", f"versione: {sha}")
    r = git("push", "origin", "main")
    out = (r.stdout or "") + (r.stderr or "")
    print("push:", out.strip().splitlines()[-1] if out.strip() else "ok")
    if r.returncode != 0:
        print("ERRORE PUSH:", out[-600:])
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
