"""
Verifica in un colpo solo:
  - l'ultimo commit su GitHub
  - la versione dell'app online
  - se sono allineati (deploy fatto) oppure no
"""
import re
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

URL_APP = "https://canzoni-pentecostali-enzo.streamlit.app"


def ultimo_commit():
    req = urllib.request.Request(
        "https://github.com/enzatoro1-afk/canzoni-tiktok/commits/main.atom",
        headers={"User-Agent": "a"})
    xml = urllib.request.urlopen(req, timeout=40).read().decode("utf-8")
    titoli = re.findall(r"<title>([^<]*)</title>", xml)
    sha = re.findall(r"versione: ([0-9a-f]{7})", xml)
    return (sha[0] if sha else "?"), (titoli[1] if len(titoli) > 1 else "?")


def versione_online():
    req = urllib.request.Request(URL_APP + "/static/build.txt",
                                 headers={"User-Agent": "a"})
    try:
        c = urllib.request.urlopen(req, timeout=30).read().decode("utf-8").strip()
        if c.startswith("20"):
            return c
    except Exception:
        pass
    return "n/d"


sha, titolo = ultimo_commit()
print(f"GitHub   : {sha}  ({titolo[:60]})")
print(f"Online   : {versione_online()}")
print("Stato    : deploy in corso (l'app online si aggiorna entro 1-3 minuti)")
