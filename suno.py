# -*- coding: utf-8 -*-
"""
suno.py
=======
Generazione del cantico con SUNO, usando i crediti gratuiti giornalieri del
tuo account.

Perche' funziona senza installare niente:
    suno.com non ha un'API pubblica per gli account gratuiti, ma la sua app
    web parla con un'API interna. Questo modulo fa esattamente quello che
    fa l'app web del browser:
      - manda il tuo cookie di sessione (__session) come "Bearer"
      - aggiunge l'header "Browser-Token" (timestamp in base64): e' quello
        che evita che Suno chieda il CAPTCHA
      - chiama /api/generate/v2/ per generare, poi /api/feed/v2/ per sapere
        quando e' pronto, e scarica l'audio (media_urls)

Cosa ti serve (una volta sola):
    il tuo cookie di suno.com, salvato nel file ".suno_cookie.txt" (nella
    cartella dell'app). Il file e' in .gitignore: il cookie NON finisce su
    GitHub e non passa dalla chat.

    Il cookie vale circa un'ora: quando scade l'app lo dice e basta
    rinnovarlo (vedi AGGIORNA_COOKIE_SUNO.py).

Alternativa: se preferisci usare il servizio open source "suno-api" che
gira in locale sulla porta 8000, l'app lo usa come riserva.
"""

from __future__ import annotations

import base64
import json
import os
import re
import tempfile
import time
import uuid

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore


# --------------------------------------------------------------------------
# I TAG FISSI: il sound che vogliamo per un cantico evangelico
# --------------------------------------------------------------------------

STILE_CHIESA = ("Modern Christian Worship, contemporary gospel, inspiring, "
                "uplifting, powerful vocal harmony, emotional, "
                "Christian Worship, Gospel, Italian vocal")

STRUMENTI = ("Acoustic guitar, ambient piano, cinematic synths, "
              "build-up drums, emotional strings")

# gli altri tag che aggiungiamo: lingua italiana, voce, qualita'
TAG_AGGIUNTI = "Italian vocals, female and male vocal harmony, worship, "
TAG_AGGIUNTI += "prayer, devotional, studio quality, no spoken intro"

TUTTI_I_TAG = (f"{STILE_CHIESA}, {STRUMENTI}, {TAG_AGGIUNTI}")

# --------------------------------------------------------------------------
# La struttura: il testo diventa [Verse] + [Chorus]
# --------------------------------------------------------------------------


def _ripulisci_lyrics(testo: str) -> str:
    """Toglie prefissi, codici, commenti. Lascia solo le righe del brano."""
    t = (testo or "").strip()
    if not t:
        return ""
    if "```" in t:
        parti = t.split("```")
        t = (parti[1] if len(parti) > 1 else t)
    righe = []
    for r in t.split("\n"):
        r = r.strip()
        if not r:
            continue
        if r.startswith("["):
            righe.append(r)
            continue
        # scarta le frasi di spiegazione
        if re.match(r"^(ecco|certo|sure|ok|bene|incluso|ecco il|testo|canzone|"
                    r"here|verse|chorus)", r, re.IGNORECASE) and len(r) < 70:
            continue
        righe.append(r)
    return "\n".join(righe)


def struttura_canzone(testo: str) -> str:
    """
    Trasforma il testo in un brano con struttura.

    - se il testo ha gia' [Verse]/[Chorus] -> lo tiene (e lo pulisce)
    - altrimenti lo divide: meta' -> [Verse 1], il resto -> [Chorus]
      (un testo lungo viene diviso in piu' strofe + un ritornello finale)
    """
    pulito = _ripulisci_lyrics(testo)
    if not pulito:
        return ""
    if "[Verse" in pulito or "[Chorus" in pulito:
        return pulito

    # divide il testo in frasi (ogni riga = un verso)
    versi = [r for r in pulito.split("\n") if r.strip()]
    if len(versi) < 2:
        return "[Verse]\n" + pulito

    meta = max(1, len(versi) // 2)
    strofe = versi[:meta]
    resto = versi[meta:] or versi[-1:]

    out = ["[Verse]"]
    out += strofe
    # se il testo e' lungo, una seconda strofa
    if len(resto) > 4:
        out.append("")
        out.append("[Verse 2]")
        out += resto[:len(resto) // 2]
        resto = resto[len(resto) // 2:]
    out.append("")
    out.append("[Chorus]")
    out += resto
    return "\n".join(out)


# --------------------------------------------------------------------------
# Il contatto con Suno
# --------------------------------------------------------------------------

API_SUNO = "https://studio-api.prod.suno.com"
SERVIZIO_LOCALE = "http://localhost:8000"   # il servizio open source (riserva)

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")


def _percorso_cookie() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        ".suno_cookie.txt")


def _cookie_grezzo() -> str:
    """
    Il cookie di sessione di suno.com.

    Lo cerca in tre posti, in quest'ordine:
      1) la sessione del browser (se l'utente lo ha incollato nell'app)
      2) il file locale .suno_cookie.txt (in .gitignore)
      3) la variabile d'ambiente SUNO_COOKIE
    """
    try:
        import streamlit as st
        v = str(st.session_state.get("cookie_suno", "") or "").strip()
        if v:
            return v
    except Exception:
        pass
    try:
        p = _percorso_cookie()
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                v = f.read().strip()
            if v:
                return v
    except Exception:
        pass
    return (os.environ.get("SUNO_COOKIE", "") or "").strip()


def salva_cookie_suno(cookie: str) -> str:
    """
    Salva il cookie di suno.com nel file locale (se si puo').
    Restituisce un messaggio per l'utente.
    """
    cookie = (cookie or "").strip()
    if len(cookie) < 20 or "=" not in cookie:
        return "Il cookie sembra incompleto: incolla tutta la riga."
    try:
        with open(_percorso_cookie(), "w", encoding="utf-8", newline="\n") as f:
            f.write(cookie)
    except Exception as exc:
        return (f"Salvato solo per questa sessione (non sono riuscito a "
                f"scrivere il file: {exc})")
    return "Cookie salvato sul computer (file .suno_cookie.txt, in .gitignore)."


def cookie_suno_scaduto() -> bool:
    """True se il cookie non c'e' piu' o non e' piu' valido."""
    ok, _nota = suno_disponibile()
    return not ok


def _cookie_dict() -> dict:
    """Il cookie diviso in chiave -> valore."""
    grezzo = _cookie_grezzo()
    out = {}
    for parte in grezzo.split(";"):
        parte = parte.strip()
        if "=" in parte:
            k, v = parte.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def _browser_token() -> str:
    """
    L'header che fa l'app web di Suno. Senza questo Suno chiede il CAPTCHA
    e la generazione fallisce.
    Il valore e' {"token": base64({"timestamp": <millisecondi>})}.
    """
    ts = int(time.time() * 1000)
    interno = base64.b64encode(
        json.dumps({"timestamp": ts}, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    return json.dumps({"token": interno}, separators=(",", ":"))


def _headers() -> dict:
    cookie = _cookie_dict()
    token = cookie.get("__session", "")
    device = cookie.get("ajs_anonymous_id", "")
    h = {
        "Content-Type": "application/json",
        "Accept-Language": "en",
        "User-Agent": USER_AGENT,
        "Browser-Token": _browser_token(),
    }
    if token:
        h["Authorization"] = f"Bearer {token}"
    if device:
        h["Device-Id"] = f'"{device}"'
    return h


def _sessione_scaduta(messaggio: str) -> bool:
    """Il token di ~1 ora e' scaduto: serve rinnovare il cookie."""
    m = (messaggio or "").lower()
    return ("401" in m or "403" in m or "unauthorized" in m
            or "forbidden" in m or "expired" in m)


def suno_disponibile() -> tuple:
    """Controlla che il cookie sia valido e dice quanti crediti restano."""
    if requests is None:
        return False, "requests non installato"
    if not _cookie_grezzo():
        return False, ("manca il cookie di suno.com (file .suno_cookie.txt). "
                       "L'app te lo spiega nella barra laterale.")
    try:
        r = requests.get(f"{API_SUNO}/api/billing/info/", headers=_headers(),
                         cookies=_cookie_dict(), timeout=20)
        if r.status_code == 200:
            d = r.json()
            crediti = d.get("total_credits_left")
            if crediti is None:
                crediti = d.get("credits")
            if crediti is None:
                crediti = (d.get("monthly_limit", 0) or 0) - \
                    (d.get("monthly_usage", 0) or 0)
            return True, f"crediti gratuiti rimasti: {crediti}"
        if _sessione_scaduta(str(r.status_code)):
            return False, ("la sessione di Suno e' scaduta (dura ~1ora): "
                           "va rinnovata il cookie")
        return False, f"suno non risponde ({r.status_code})"
    except Exception as exc:
        # nessuna rete? prova il servizio open source in locale
        try:
            s = requests.get(f"{SERVIZIO_LOCALE}/api/get_limit", timeout=8)
            if s.status_code == 200:
                return True, "servizio open source in locale"
        except Exception:
            pass
        return False, (f"impossibile contattare suno.com: {str(exc)[:90]}")


def _genera_endpoint_web(lyrics: str, tags: str, h: dict, cookie: dict):
    """L'endpoint che usa oggi la pagina web di Suno (riserva)."""
    corpo = {
        "token": None,
        "generation_type": "TEXT",
        "title": "",
        "tags": tags or "",
        "negative_tags": "",
        "mv": "chirp-v3-5",
        "prompt": lyrics,
        "make_instrumental": False,
        "user_uploaded_images_b64": None,
        "metadata": {
            "web_client_pathname": "/create",
            "create_surface": "desktop_create_form",
            "is_max_mode": False,
            "is_mumble": False,
            "create_mode": "custom",
            "disable_volume_normalization": False,
            "control_sliders": {"aug_creativity": 1},
        },
        "override_fields": [],
        "cover_clip_id": None,
        "continue_clip_id": None,
        "continue_at": None,
    }
    try:
        return requests.post("https://suno.com/a/api/generate/v2-web/",
                             json=corpo, headers=h, cookies=cookie, timeout=60)
    except Exception:
        return None


def _genera_via_api(lyrics: str, tags: str, timeout: int) -> dict:
    """Genera il brano chiamando l'API di Suno (come fa l'app web)."""
    vuoto = {"ok": False, "errore": "", "file": "", "url": "", "motore": "Suno"}
    cookie = _cookie_dict()
    h = _headers()

    # 1) la richiesta di generazione
    corpo = {
        "make_instrumental": False,
        "mv": "chirp-v3-5",
        "prompt": f"{tags}\n\n{lyrics}" if tags else lyrics,
        "generation_type": "TEXT",
        "continue_at": None,
        "continue_clip_id": None,
        "task": None,
        "token": None,
    }
    # Suno limita quante canzoni si generano di fila: risponde 422
    # ("Token validation failed"). In quel caso aspettiamo e riprovare.
    r = None
    for _tentativo in range(3):
        try:
            r = requests.post(f"{API_SUNO}/api/generate/v2/", json=corpo,
                              headers=h, cookies=cookie, timeout=60)
        except Exception as exc:
            return {**vuoto,
                    "errore": f"Suno non ha risposto: {str(exc)[:150]}"}
        if r.status_code != 422:
            break
        if _tentativo < 2:
            _attesa = 45 * (_tentativo + 1)
            print(f"[suno] Suno chiede una pausa: attendo {_attesa}s e riprovo")
            time.sleep(_attesa)
            h = _headers()

    if r is None:
        return {**vuoto, "errore": "Suno non ha risposto"}

    if r.status_code in (401, 403):
        return {**vuoto, "errore": (
            "Suno: la sessione e' scaduta (il cookie vale ~1ora). "
            "Rinnovala dalla barra laterale e riprova.")}
    if r.status_code == 402:
        return {**vuoto, "errore": ("Suno: crediti giornalieri esauriti. "
                                   "aspetta domani o ricarica")}
    if r.status_code == 422:
        return {**vuoto, "errore": (
            "Suno: hai generato troppe canzoni di fila e ti ha fermato per "
            "qualche minuto. Aspetta 3-5 minuti e premi di nuovo "
            "'Componi e canta' (le canzoni gia' fatte sono nella tua "
            "libreria su suno.com).")}
    if r.status_code != 200:
        # l'endpoint vecchio potrebbe non esistere piu': prova quello che
        # usa oggi la pagina web di Suno
        _altro = _genera_endpoint_web(lyrics, tags, h, cookie)
        if _altro is None:
            return {**vuoto, "errore": f"Suno errore {r.status_code}: "
                                       f"{r.text[:150]}"}
        r = _altro
    if r.status_code in (401, 403):
        return {**vuoto, "errore": (
            "Suno: la sessione e' scaduta (il cookie vale ~1ora). "
            "Rinnovala dalla barra laterale e riprova.")}
    if r.status_code == 402:
        return {**vuoto, "errore": ("Suno: crediti giornalieri esauriti. "
                                   "aspetta domani o ricarica")}
    if r.status_code != 200:
        # l'endpoint vecchio potrebbe non esistere piu': prova quello che
        # usa oggi la pagina web di Suno
        r = _genera_endpoint_web(lyrics, tags, h, cookie)
        if r is None:
            return {**vuoto,
                    "errore": f"Suno errore {r.status_code}: {r.text[:150]}"}

    try:
        d = r.json()
    except Exception:
        return {**vuoto, "errore": "risposta Suno non leggibile"}

    clip = (d.get("clips") or [{}])[0]
    id_brano = clip.get("id")
    if not id_brano:
        return {**vuoto, "errore": "Suno non ha restituito il brano"}

    # 2) aspetto che sia pronto
    scaduto = time.time() + timeout
    url_audio = ""
    stato = ""
    while time.time() < scaduto:
        time.sleep(4)
        try:
            g = requests.get(f"{API_SUNO}/api/feed/v2",
                             params={"ids": id_brano}, headers=_headers(),
                             cookies=_cookie_dict(), timeout=30)
            if g.status_code != 200:
                continue
            brani = g.json().get("clips") or []
            if not brani:
                continue
            b = brani[0]
            stato = str(b.get("status", ""))
            if stato == "error":
                return {**vuoto, "errore": "Suno: generazione fallita"}
            # l'audio vero e' in media_urls (audio_url e' vuoto)
            for m in (b.get("media_urls") or []):
                u = m.get("url")
                if u and str(u).startswith("http"):
                    url_audio = str(u)
                    break
            if not url_audio:
                for chiave in ("video_url", "audio_url"):
                    u = b.get(chiave)
                    if u and str(u).startswith("http") and "forbidden" not in str(u):
                        url_audio = str(u)
                        break
            if url_audio and stato in ("complete", "streaming"):
                break
        except Exception:
            continue

    if not url_audio:
        return {**vuoto, "errore": (
            f"Suno non ha finito il brano (stato: {stato or 'sconosciuto'}). "
            "Riprova fra un minuto.")}

    # 3) scarico l'audio
    try:
        est = ".mp3" if url_audio.lower().endswith(".mp3") else ".m4a"
        out = os.path.join(tempfile.gettempdir(),
                           f"suno_{uuid.uuid4().hex[:10]}{est}")
        rr = requests.get(url_audio, stream=True, timeout=240)
        if rr.status_code != 200:
            return {**vuoto, "errore": f"download non riuscito ({rr.status_code})"}
        con_piu = 0
        with open(out, "wb") as f:
            for pezzo in rr.iter_content(65536):
                if pezzo:
                    f.write(pezzo)
                    con_piu += len(pezzo)
        # Suno protegge l'audio con una cifratura (DRM): il file scaricato
        # NON e' un mp3/m4a leggibile. In quel caso lo diciamo chiaramente.
        with open(out, "rb") as f:
            testa = f.read(16)
        if b"ftyp" not in testa and b"OggS" not in testa and con_piu > 5000:
            try:
                os.remove(out)
            except Exception:
                pass
            return {**vuoto, "errore": (
                "Suno ha protetto l'audio (cifratura): il brano e' pronto e si "
                "ascolta nella tua libreria su suno.com, ma il file non si "
                "puo' scaricare. Aprilo da suno.com e caricalo qui sotto per "
                "il video."), "file": "", "url": url_audio,
                "motore": "Suno (i tuoi crediti gratuiti)",
                "protegto": True}
    except Exception as exc:
        return {**vuoto, "errore": f"download fallito: {exc}"}

    return {"ok": True, "errore": "", "file": out, "url": url_audio,
            "motore": "Suno (i tuoi crediti gratuiti)"}


def _genera_via_servizio(lyrics: str, tags: str, timeout: int) -> dict:
    """La riserva: il servizio open source 'suno-api' in locale (porta 8000)."""
    vuoto = {"ok": False, "errore": "", "file": "", "url": "", "motore": "Suno"}
    try:
        h = {"Content-Type": "application/json"}
        c = _cookie_grezzo()
        if c:
            h["Cookie"] = c
        r = requests.post(
            f"{SERVIZIO_LOCALE}/api/generate",
            json={"prompt": f"{tags}\n\n{lyrics}" if tags else lyrics,
                  "make_instrumental": False, "model": "chirp-v3-5",
                  "wait_audio": True},
            headers=h, timeout=timeout)
        if r.status_code != 200:
            return {**vuoto, "errore": f"servizio Suno: {r.status_code}"}
        dati = r.json()
        brani = dati if isinstance(dati, list) else (dati.get("data") or [])
        urls = [b.get("audio_url") for b in brani
                if isinstance(b, dict) and b.get("audio_url")]
        if not urls:
            return {**vuoto, "errore": "il servizio Suno non ha restituito l'audio"}
        out = os.path.join(tempfile.gettempdir(),
                           f"suno_{uuid.uuid4().hex[:10]}.mp3")
        rr = requests.get(urls[0], stream=True, timeout=240)
        with open(out, "wb") as f:
            for pezzo in rr.iter_content(65536):
                if pezzo:
                    f.write(pezzo)
        return {"ok": True, "errore": "", "file": out, "url": urls[0],
                "motore": "Suno (servizio locale)"}
    except Exception as exc:
        return {**vuoto, "errore": f"servizio Suno: {str(exc)[:120]}"}


def genera_canzone_suno(lyrics: str, tags: str = "", titolo: str = "",
                        timeout: int = 420, attendo: bool = True) -> dict:
    """
    Genera il cantico con Suno (crediti gratuiti del tuo account).

    Restituisce {"ok": True, "file": "<audio>", "url": "...", "motore": "Suno"}
    oppure {"ok": False, "errore": "..."}
    """
    vuoto = {"ok": False, "errore": "", "file": "", "url": "", "motore": "Suno"}
    if requests is None:
        return {**vuoto, "errore": "requests non installato"}

    lyrics = struttura_canzone(lyrics)
    if len(lyrics) < 10:
        return {**vuoto, "errore": "Il testo del brano e' troppo corto."}

    tags = tags or TUTTI_I_TAG
    titolo = (titolo or "CANTICO")[:80]

    # 1) l'API diretta (funziona senza installare nulla)
    r = _genera_via_api(lyrics, tags, timeout)
    if r.get("ok"):
        return r
    # l'audio e' protetto da Suno: non serve riprovare con il servizio
    if r.get("protegto"):
        return r

    # 2) la riserva: il servizio open source in locale
    try:
        s = requests.get(f"{SERVIZIO_LOCALE}/api/get_limit", timeout=6)
        vivo = s.status_code == 200
    except Exception:
        vivo = False
    if vivo:
        r2 = _genera_via_servizio(lyrics, tags, timeout)
        if r2.get("ok"):
            return r2
        return {**vuoto, "errore": (f"{r.get('errore', '')} | "
                                    f"{r2.get('errore', '')}")}

    return {**vuoto, "errore": r.get("errore", "Suno non ha risposto")}
