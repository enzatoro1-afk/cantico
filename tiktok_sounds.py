# -*- coding: utf-8 -*-
"""
tiktok_sounds.py
================
Ricerca dei brani nella libreria audio di TikTok.

NOTA TECNICA (importante):
    La libreria audio di TikTok NON è interrogabile da server in modo
    "pulito": gli endpoint interni (/api/search/general/full, /api/music/*)
    richiedono una firma anti-bot del dispositivo (X-Bogus / X-Gorgon) e
    rispondono con corpo vuoto se manca. Per questo:

      1. questo modulo TENTA comunque gli endpoint pubblici a ogni ricerca
         (se TikTok li riapre, l'app li usa da sola, senza modifiche);
      2. se non è disponibile, l'app non si blocca: passa i titoli trovati
         su YouTube (che sono gli stessi titoli presenti nella libreria audio
         di TikTok) e apre la RICERCA AUDIO DI TIKTOK con un tocco.

    Il link diretto è la parte importante: l'utente tocca "Cerca su TikTok",
    si apre la ricerca dei suoni già impostata sul titolo esatto della canzone
    e sceglie l'audio da usare nella pubblicazione.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote_plus

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore

TIMEOUT = 20

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
    "Referer": "https://www.tiktok.com/",
}

MESSAGGIO_TIKTOK = (
    "TikTok non permette a un'app esterna di leggere la libreria audio "
    "(protegge i suoi dati con una firma anti-bot). Per questo l'app ti "
    "porta con un tocco alla ricerca dei suoni di TikTok, già impostata sul "
    "titolo esatto della canzone: ti basta scegliere l'audio e pubblicare."
)


@dataclass
class SoundTikTok:
    """Un brano trovato nella libreria audio di TikTok."""

    titolo: str
    autore: str = ""
    url: str = ""
    durata: str = ""

    @property
    def url_ricerca(self) -> str:
        return link_ricerca_audio(self.titolo)


# --------------------------------------------------------------------------
# Link ufficiali verso TikTok
# --------------------------------------------------------------------------

def link_ricerca_audio(titolo: str) -> str:
    """Apre la ricerca dei suoni di TikTok sul titolo indicato."""
    return f"https://www.tiktok.com/music?q={quote_plus(titolo)}"


def link_ricerca_video(query: str) -> str:
    """
    Apre la ricerca VIDEO di TikTok (per vedere come gli altri hanno fatto
    il video su quella canzone o su quel testo: il formato che funziona).

    Serve al creator per ispirarsi, NON per ricaricare i video degli altri:
    per usare la musica, il modo giusto e' prendere il suono originale dalla
    libreria audio di TikTok.
    """
    return f"https://www.tiktok.com/search?q={quote_plus(query)}"


def link_upload(caption: str = "") -> str:
    """Apre l'area di creazione di un nuovo video su TikTok."""
    base = "https://www.tiktok.com/upload"
    if caption:
        return f"{base}?caption={quote_plus(caption[:150])}"
    return base


def link_sound(sound_id: str) -> str:
    """Apre la pagina di un suono specifico di TikTok."""
    return f"https://www.tiktok.com/sound/{sound_id}"


# --------------------------------------------------------------------------
# Endpoint pubblici tentati a ogni ricerca
# --------------------------------------------------------------------------

def _prova_endpoint(url: str, params: dict) -> list[SoundTikTok]:
    """Esegue una chiamata e prova a ricavare brani da un JSON qualsiasi."""
    if requests is None:
        return []
    try:
        risposta = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
    except Exception:
        return []
    if risposta.status_code != 200 or not risposta.text.strip():
        return []
    try:
        risposta.encoding = "utf-8"
        dati = risposta.json()
    except Exception:
        return []
    return _estrai_suoni(dati)


def _estrai_suoni(dati) -> list[SoundTikTok]:
    """Cerca, in profondità nel JSON, oggetti che descrivono un brano."""
    trovati: list[SoundTikTok] = []
    visti: set[str] = set()

    def walk(o):
        if isinstance(o, dict):
            titolo = None
            for chiave in ("title", "soundTitle", "musicName", "musicTitle", "name"):
                valore = o.get(chiave)
                if isinstance(valore, str) and valore.strip():
                    titolo = valore.strip()
                    break
            if titolo:
                autore = ""
                for chiave in ("authorName", "author", "soundAuthor", "artistName",
                               "musicAuthor", "username"):
                    valore = o.get(chiave)
                    if isinstance(valore, str) and valore.strip():
                        autore = valore.strip()
                        break
                    if isinstance(valore, dict):
                        sotto = valore.get("displayName") or valore.get("uniqueId")
                        if isinstance(sotto, str):
                            autore = sotto
                            break
                sound_id = str(o.get("id") or o.get("soundId") or o.get("musicId") or "")
                chiave_unica = (titolo, autore)
                if chiave_unica not in visti:
                    visti.add(chiave_unica)
                    durata = ""
                    durata_raw = o.get("duration") or o.get("durationSeconds")
                    if isinstance(durata_raw, (int, float)):
                        durata = f"{int(durata_raw)//60}:{int(durata_raw)%60:02d}"
                    trovati.append(
                        SoundTikTok(
                            titolo=titolo,
                            autore=autore,
                            durata=durata,
                            url=link_sound(sound_id) if sound_id else
                                link_ricerca_audio(titolo),
                        )
                    )
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for item in o:
                walk(item)

    walk(dati)
    return trovati


def cerca_suoni_tiktok(query: str, max_risultati: int = 5) -> list[SoundTikTok]:
    """
    Tenta di trovare suoni reali nella libreria audio di TikTok.
    Se gli endpoint non rispondono (situazione attuale più comune),
    restituisce una lista vuota: l'app userà comunque i link diretti.
    """
    query = (query or "").strip()
    if not query:
        return []

    candidati = [
        # Creative Center: suggerimenti sound (trending + correlati)
        ("https://ads.tiktok.com/creative_radar_api/v1/popular_trend/sound/suggest",
         {"keyword": query, "period": 7, "limit": max_risultati, "page": 1,
          "country_code": "IT"}),
        # Creative Center: elenco sound trending
        ("https://ads.tiktok.com/creative_radar_api/v1/popular_trend/sound/list",
         {"period": 7, "limit": max_risultati, "page": 1, "country_code": "IT",
          "sort_by": "vv"}),
        # Endpoint musicale interno (se TikTok lo riapre)
        ("https://www.tiktok.com/api/music/search/",
         {"keyword": query, "count": max_risultati, "aid": 1988,
          "app_name": "tiktok_web"}),
    ]

    for url, params in candidati:
        suoni = _prova_endpoint(url, params)
        if suoni:
            return suoni[:max_risultati]
    return []
