# -*- coding: utf-8 -*-
"""
tiktok_pubblica.py
==================
Pubblicare il video su TikTok DIRETTAMENTE dall'app, senza dover aprire
TikTok Studio a mano.

Usa la "Content Posting API - Direct Post" di TikTok:
  1. l'utente collega il suo TikTok una volta sola (OAuth);
  2. l'app manda il video con la caption gia' scritta;
  3. l'app aspetta la risposta di TikTok e ti dice com'e' andata.

PERCHE' Serve una "developer app" di TikTok:
  TikTok permette la pubblicazione automatica SOLO a chi ha creato un'app
  da sviluppatore e l'ha fatta approvare (serve la revisione di TikTok:
  qualche giorno o qualche settimana). Senza approvazione l'API risponde
  "unaudited_client_can_only_post_to_private_accounts": i video si
  pubblicano ma SOLO in privato.

  COME SI FA (una volta sola):
  1. https://developers.tiktok.com  -> crea un'app (gratis)
  2. attiva "Content Posting API" -> Direct Post
  3. chiedi l'approvazione dello scope "video.publish"
  4. metti le chiavi nei Secrets di Streamlit Cloud:
       TIKTOK_CLIENT_KEY     = "..."
       TIKTOK_CLIENT_SECRET  = "..."
       TIKTOK_REDIRECT_URI  = "https://la-tua-app.streamlit.app/"

  Finche' non e' pronto, l'app ti offre la strada SEMPLICE: scarica il
  video e apri TikTok Studio col testo gia' scritto.
"""

from __future__ import annotations

import json
import os
import time
from urllib.parse import quote, urlencode

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

API = "https://open.tiktokapis.com"
AUTORE = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_URL = f"{API}/v2/oauth/token/"
CREATOR_INFO = f"{API}/v2/post/publish/creator_info/query/"
VIDEO_INIT = f"{API}/v2/post/publish/video/init/"
STATUS_FETCH = f"{API}/v2/post/publish/status/fetch/"

SCOPE = "video.publish"

# la privacy: il primo nome e' quello che vede l'utente
PRIVACY = {
    "PUBLIC_TO_EVERYONE": "Pubblico (tutti)",
    "FOLLOWER_OF_CREATOR": "Solo chi ti segue",
    "MUTUAL_FOLLOW_FRIENDS": "Amici reciproci",
    "SELF_ONLY": "Solo io (privato)",
}


# --------------------------------------------------------------------------
# Le chiavi (dai Secrets del Cloud)
# --------------------------------------------------------------------------

def _segreto(nome: str) -> str:
    try:
        import streamlit as st
        return str(st.secrets.get(nome, "") or "").strip()
    except Exception:
        return ""


def chiavi() -> dict:
    """Le chiavi della developer app di TikTok (se ci sono)."""
    return {
        "client_key": _segreto("TIKTOK_CLIENT_KEY"),
        "client_secret": _segreto("TIKTOK_CLIENT_SECRET"),
        "redirect_uri": _segreto("TIKTOK_REDIRECT_URI"),
    }


def collegato() -> bool:
    """True se la developer app e' configurata (si puo' pubblicare)."""
    _k = chiavi()
    return bool(_k["client_key"] and _k["client_secret"] and _k["redirect_uri"])


# --------------------------------------------------------------------------
# Il link per aprire TikTok Studio (la strada semplice)
# --------------------------------------------------------------------------

def link_studio(caption: str = "") -> str:
    """Apre TikTok Studio con la caption gia' scritta dentro."""
    _base = "https://www.tiktok.com/tiktokstudio/upload"
    if caption:
        return f"{_base}?{urlencode({'caption': caption[:1500]})}"
    return _base


# --------------------------------------------------------------------------
# OAuth: collegare il proprio TikTok
# --------------------------------------------------------------------------

def url_authorize(state: str = "") -> str:
    """Il link che apre TikTok per l'autorizzazione."""
    _k = chiavi()
    if not _k["client_key"]:
        return ""
    _p = {
        "client_key": _k["client_key"],
        "response_type": "code",
        "scope": SCOPE,
        "redirect_uri": _k["redirect_uri"],
        "state": state or "cantico",
    }
    return f"{AUTORE}?{urlencode(_p)}"


def scambia_code(code: str) -> dict:
    """
    Scambia il 'code' dell'autorizzazione con l'access token.

    Restituisce {"access_token","refresh_token","open_id","expires_in","errore"}
    """
    if requests is None:
        return {"access_token": "", "errore": "requests non installato"}
    _k = chiavi()
    if not (_k["client_key"] and _k["client_secret"]):
        return {"access_token": "", "errore": "developer app non configurata"}
    try:
        _r = requests.post(TOKEN_URL, data={
            "client_key": _k["client_key"],
            "client_secret": _k["client_secret"],
            "code": (code or "").strip(),
            "grant_type": "authorization_code",
            "redirect_uri": _k["redirect_uri"],
        }, timeout=60)
    except Exception as _e:
        return {"access_token": "", "errore": str(_e)[:150]}
    try:
        _d = _r.json() or {}
    except Exception:
        return {"access_token": "", "errore": f"risposta non leggibile ({_r.status_code})"}
    if not _d.get("access_token"):
        _msg = (_d.get("error_description") or _d.get("description")
             or _d.get("error") or _r.text[:150])
        return {"access_token": "", "errore": str(_msg)}
    return {
        "access_token": _d.get("access_token", ""),
        "refresh_token": _d.get("refresh_token", ""),
        "open_id": _d.get("open_id", ""),
        "expires_in": _d.get("expires_in", 0),
        "scope": _d.get("scope", ""),
        "errore": None,
    }


def creator_info(access_token: str) -> dict:
    """Chi sei su TikTok e che opzioni di privacy hai."""
    if requests is None or not access_token:
        return {"errore": "nessun token"}
    try:
        _r = requests.post(CREATOR_INFO, headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        }, json={}, timeout=45)
        _d = _r.json() or {}
    except Exception as _e:
        return {"errore": str(_e)[:150]}
    if (_d.get("error") or {}).get("code") not in ("ok", None):
        return {"errore": (_d.get("error") or {}).get("message", "errore")}
    _data = _d.get("data") or {}
    return {
        "username": _data.get("creator_username", ""),
        "nickname": _data.get("creator_nickname", ""),
        "avatar": _data.get("creator_avatar_url", ""),
        "privacy": _data.get("privacy_level_options") or ["SELF_ONLY"],
        "duet_disabled": _data.get("duet_disabled", False),
        "stitch_disabled": _data.get("stitch_disabled", False),
        "comment_disabled": _data.get("comment_disabled", False),
        "max_durata": _data.get("max_video_post_duration_sec", 0),
        "errore": None,
    }


# --------------------------------------------------------------------------
# PUBBLICARE
# --------------------------------------------------------------------------

def pubblica(file_video: str, access_token: str, caption: str = "",
             privacy: str = "SELF_ONLY", is_aigc: bool = False) -> dict:
    """
    pubblica il video su TikTok.

    Restituisce {"ok": bool, "publish_id": str, "messaggio": str}
    """
    if requests is None:
        return {"ok": False, "publish_id": "", "messaggio": "requests mancante"}
    if not access_token:
        return {"ok": False, "publish_id": "",
                "messaggio": "TikTok non e' collegato: premi prima "
                             "'Collega il tuo TikTok'."}
    if not os.path.exists(file_video):
        return {"ok": False, "publish_id": "", "messaggio": "File video non trovato."}

    _size = os.path.getsize(file_video)
    # i file grandi si mandano a pezzi (100 MB per pezzo)
    _chunk = min(_size, 100 * 1024 * 1024)
    _n_chunk = max(1, (_size + _chunk - 1) // _chunk)

    _post_info = {
        "privacy_level": privacy or "SELF_ONLY",
        "title": (caption or "")[:2200],
        "disable_duet": False,
        "disable_comment": False,
        "disable_stitch": False,
        "brand_content_toggle": False,
        "brand_organic_toggle": False,
    }
    if is_aigc:
        _post_info["is_aigc"] = True

    _corpo = {
        "post_info": _post_info,
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": _size,
            "chunk_size": _chunk,
            "total_chunk_count": _n_chunk,
        },
    }
    try:
        _r = requests.post(VIDEO_INIT, headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        }, json=_corpo, timeout=90)
        _d = _r.json() or {}
    except Exception as _e:
        return {"ok": False, "publish_id": "", "messaggio": str(_e)[:180]}
    _err = _d.get("error") or {}
    if _err.get("code") not in ("ok", None) or not _d.get("data"):
        _msg = _err.get("message") or _r.text[:200]
        return {"ok": False, "publish_id": "",
                "messaggio": f"TikTok ha rifiutato: {_msg}"}

    _publish_id = _d["data"].get("publish_id", "")
    _upload_url = _d["data"].get("upload_url", "")

    # ---- mando il file a TikTok ----
    if _upload_url:
        try:
            with open(file_video, "rb") as _f:
                _dati = _f.read()
            _h = {
                "Content-Type": "video/mp4",
                "Content-Length": str(len(_dati)),
                "Content-Range": f"bytes 0-{len(_dati)-1}/{len(_dati)}",
            }
            _u = requests.put(_upload_url, headers=_h, data=_dati, timeout=600)
            if _u.status_code not in (200, 201, 204):
                return {"ok": False, "publish_id": _publish_id,
                        "messaggio": f"Caricamento del file fallito "
                                     f"({_u.status_code})"}
        except Exception as _e:
            return {"ok": False, "publish_id": _publish_id,
                    "messaggio": f"Errore nel caricamento: {str(_e)[:150]}"}

    # ---- aspetto che TikTok finisca ----
    for _ in range(12):
        time.sleep(5)
        _s = _stato(_publish_id, access_token)
        if _s.get("stato") in ("PUBLISH_COMPLETE", "COMPLETE"):
            return {"ok": True, "publish_id": _publish_id,
                    "messaggio": "Pubblicato! Lo trovi su TikTok fra un "
                                 "momento."}
        if _s.get("stato") in ("FAILED", "PUBLISH_FAILED"):
            return {"ok": False, "publish_id": _publish_id,
                    "messaggio": "TikTok ha rifiutato il video: " +
                                 str(_s.get("errore", ""))[:200]}

    return {"ok": True, "publish_id": _publish_id,
            "messaggio": "Video mandato a TikTok: sta controllando la "
                         "pubblicazione. Controlla fra un minuto su TikTok."}


def _stato(publish_id: str, access_token: str) -> dict:
    """Lo stato della pubblicazione."""
    if not (publish_id and access_token) or requests is None:
        return {"stato": "", "errore": ""}
    try:
        _r = requests.post(STATUS_FETCH, headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        }, json={"publish_id": publish_id}, timeout=45)
        _d = _r.json() or {}
    except Exception as _e:
        return {"stato": "", "errore": str(_e)[:150]}
    _data = _d.get("data") or {}
    _err = _d.get("error") or {}
    return {
        "stato": _data.get("status", ""),
        "errore": _err.get("message", ""),
    }


# --------------------------------------------------------------------------
# Il token vive nel BROWSER di chi lo ha autorizzato (non sul server)
# --------------------------------------------------------------------------

SCRIPT_SALVA_TOKEN = """
<script>
(function () {
  try { localStorage.setItem("cantico_tiktok_token", "__TOKEN__"); } catch (e) {}
})();
</script>
"""

SCRIPT_LEGGI_TOKEN = """
<script>
(function () {
  try {
    if (window.__canticoTtMesso) return;
    window.__canticoTtMesso = true;
    function prova() {
      var t = localStorage.getItem("cantico_tiktok_token");
      if (!t) return;
      var campi = document.querySelectorAll('input[type="password"]');
      for (var i = 0; i < campi.length; i++) {
        var lab = campi[i].closest('div[data-testid="stTextInput"]');
        if (!lab || ((lab.textContent || lab.innerText) || "").indexOf("token TikTok") < 0) continue;
        if (campi[i].value) return;
        var proto = Object.getPrototypeOf(campi[i]);
        var setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
        setter.call(campi[i], t);
        campi[i].dispatchEvent(new Event('input', { bubbles: true }));
        return;
      }
      setTimeout(prova, 300);
    }
    setTimeout(prova, 100);
  } catch (e) {}
})();
</script>
"""
