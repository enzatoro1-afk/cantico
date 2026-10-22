# -*- coding: utf-8 -*-
"""
app.py
======
ASSISTENTE CANZONI PENTECOSTALI PER TIKTOK
--------------------------------------------
Web app (Streamlit) in 4 passaggi:
  1. SCRIVI   -> incolli il versetto / la riflessione (con correzione gramm. auto)
  2. CERCA   -> l'app analizza il testo e cerca su YouTube + TikTok
  3. SCEGLI  -> tra le canzoni proposte, con spiegazione del perché
  4. PUBBLICA-> genero caption, hashtag, hook e ti apro TikTok pronto

Avvio locale:      python -m streamlit run app.py
Deploy gratuito:   Streamlit Community Cloud (vedi README.md)
"""

from __future__ import annotations

import hashlib
import html as html_mod
import json
import os
import re
import tempfile
from urllib.parse import quote as _quote_url
from datetime import date, datetime, timedelta

import streamlit as st

# --- hot-reload dei moduli locali ------------------------------------------
# Streamlit riesegue solo app.py, ma i moduli importati restano in
# sys.modules: se cambio youtube_search.py, senza questo blocco continua a
# girare il codice VECCHIO (stesso problema su Streamlit Cloud).
import hotreload  # noqa: E402  (deve stare PRIMA delle import locali)

_RI_CARICATI = hotreload.ricarica()

from ai_client import (chiave_da_secrets, chiave_gemini_da_secrets,
                       dimentica_chiave_gemini, fonte_chiave_gemini,
                       interpreta_con_ia,
                       interpreta_gemini, interpreta_gratis, link_chatgpt,
                       parole_chiave_dall_ia, qualita_ia, ricorda_chiave_gemini,
                       scegli_versetto_ia)
from musica import (MOTORI_GRATUITI, STILE_DEFAULT, crea_video_silenzioso,
                    crea_video_tiktok,
                    genera_canzone, genera_canzone_gratuita,
                    genera_canzone_senza_pagare)
import attiva
from suno import (STRUMENTI, STILE_CHIESA, TUTTI_I_TAG, genera_canzone_suno,
                  salva_cookie_suno, struttura_canzone, suno_disponibile)
try:
    from treblo import genera_canzone_treblo, treblo_disponibile
except Exception:  # il file potrebbe non essere ancora sul server
    def genera_canzone_treblo(lyrics, tags="", timeout=420):
        return {"ok": False, "file": "", "url": "", "motore": "Treblo",
                "errore": ("Il motore Treblo non e' ancora disponibile: "
                           "aggiorna l'app (Ricarica la versione piu' "
                           "recente) e riprova.")}

    def treblo_disponibile():
        return False, "Treblo non e' ancora disponibile su questo server."
from configura import (ISTRUZIONE_SUNO, PASSI, TESTO_SUNO, leggi_secrets,
                      scrivi_secrets, stato_configurazione)
from testi_canzone import scrivi_testi_canzone
from archivio import (aggiungi_post, cancella_archivio, carica_archivio,
                      elimina_post)
from bible_search2 import (capitoli_del, cerca_libri, cerca_passaggi,
                         testo_capitolo)
from bible_search import (NOME_TRADUZIONE, cerca_versetti,
                        testo_versetto_pulito, trova_versetto)
from post_generator import (
    FORMATI_POST,
    genera_hashtag,
    genera_hook,
    genera_caption,
    giorno_settimana,
    suggerisci_orari,
)
try:
    from riflessione import (genera_riflessione, genera_riflessione_e_post,
                             momento_migliore, riduci_per_post)
except Exception:  # il file potrebbe non essere ancora sul server
    def genera_riflessione(*_a, **_k):
        return {"testo": "", "parole_chiave": [], "fonte": "",
                "errore": "Modulo non disponibile: aggiorna l'app."}

    def genera_riflessione_e_post(*_a, **_k):
        return {"riflessione": "", "parole_chiave": [], "post": {},
                "fonte": "", "errore": "Modulo non disponibile: aggiorna l'app."}

    def riduci_per_post(*_a, **_k):
        return {"hook": "", "corpo": [], "caption": "", "cta": "",
                "fonte": "", "errore": "Modulo non disponibile: aggiorna l'app."}

    def momento_migliore(*_a, **_k):
        return {"giorno": "", "fascia": "", "orario": "", "motivo": "",
                "consiglio": "", "fonte": "",
                "errore": "Modulo non disponibile: aggiorna l'app."}

try:
    # modulo "fresco": se il server tiene in memoria la versione vecchia,
    # hotreload._modulo_fresco() la ricarica dal disco
    _setup_fresco = hotreload._modulo_fresco("setup_app")
    if _setup_fresco is not None:
        chiavi_browser = _setup_fresco.chiavi_browser
        pannello_setup = _setup_fresco.pannello_setup
    else:
        raise ImportError("setup_app non disponibile")
except Exception:  # il file potrebbe non essere ancora sul server
    def pannello_setup(*_a, **_k):
        return {"email": "", "hash": "", "gemini": "", "treblo": "",
                "hf": "", "salvato": False}

    def chiavi_browser():
        return {"gemini": "", "treblo": "", "hf": "", "email": ""}

try:
    from audio_youtube import scarica_audio
except Exception:  # il file potrebbe non essere ancora sul server
    def scarica_audio(*_a, **_k):
        return {"ok": False, "file": "",
                "errore": "Modulo audio non disponibile: aggiorna l'app."}

try:
    from immagini import genera_immagine
except Exception:  # il file potrebbe non essere ancora sul server
    def genera_immagine(*_a, **_k):
        return {"ok": False, "file": "", "fonte": "",
                "errore": "Modulo immagini non disponibile: aggiorna l'app."}
from tiktok_sounds import (
    MESSAGGIO_TIKTOK,
    cerca_suoni_tiktok,
    link_ricerca_audio,
    link_ricerca_video,
)
from studio_biblico import (
    PROMPT_INTERPRETAZIONE,
    estrai_parole_chiave_spirituali,
    estrai_spiegazione,
    genera_passi,
    interpretazione_dotrinale,
    query_studio,
    rileva_riferimento,
)
from text_tools import (
    analizza_testo,
    correggi_testo,
    query_per_salmo,
    spiega_canzone,
)
from youtube_search import (
    FILTRO_PENTECOSTALE,
    KEYWORD_NEGATIVE,
    ErroreRicerca,
    STILI,
    artista_fidato,
    cerca_interpretazioni,
    costruisci_query,
    costruisci_query_musica,
    estrai_parole_chiave,
    nome_artista,
    ricerca_multipla,
)


# script unico: delega i click sui pulsanti .copybtn (Streamlit rimuove
# gli handler inline "onclick", quindi uso un listener delegato)
SCRIPT_COPIA = """
<script>
(function(){
  if (window.__canticoCopy) { return; }
  window.__canticoCopy = true;
  document.addEventListener('click', function(ev){
    var b = ev.target && ev.target.closest ? ev.target.closest('.copybtn') : null;
    if (!b) { return; }
    var testo = b.getAttribute('data-copy') || '';
    var label = b.getAttribute('data-label') || 'Copia';
    var fatto = function(){
      b.innerHTML = '\u2705 Copiato!';
      setTimeout(function(){ b.innerHTML = label; }, 1800);
    };
    var metodo = function(){
      try {
        var ta = document.createElement('textarea');
        ta.value = testo;
        ta.setAttribute('readonly','');
        ta.style.position = 'fixed';
        ta.style.top = '-1000px';
        ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.focus();
        ta.select();
        ta.setSelectionRange(0, ta.value.length);
        var ok = document.execCommand('copy');
        document.body.removeChild(ta);
        if (ok) { fatto(); }
      } catch(e) {}
    };
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(testo).then(fatto).catch(metodo);
    } else {
      metodo();
    }
  });
})();
</script>
"""

def html(contenuto: str, js: bool = False, **kwargs) -> None:
    """
    Rende HTML grezzo.
    Uso st.html() invece di html(): st.html non
    passa da react-markdown e quindi NON causa il crash frontend
    "NotFoundError: removeChild ... not a child of this node"
    (che su Streamlit Cloud interrompeva la pagina).

    **kwargs: accetto (e ignoro) argomenti tipo unsafe_allow_html=True
    per non rompere se resta qualche chiamata col vecchio formato.
    """
    try:
        st.html(contenuto, unsafe_allow_javascript=js)
    except TypeError:      # Streamlit < 1.47: niente argomento unsafe_allow_javascript
        try:
            st.html(contenuto)
        except Exception:
            st.markdown(contenuto, unsafe_allow_html=True)
    except Exception:
        try:
            st.markdown(contenuto, unsafe_allow_html=True)
        except Exception:
            pass


# --------------------------------------------------------------------------
# Configurazione pagina
# --------------------------------------------------------------------------

AUTORE_APP = "Foster"   # <- nome da mettere in firma (cambialo qui)

# La firma puo' essere cambiata SENZA toccare il codice: metti
#   AUTORE_APP = "Il tuo nome"
# nei Secrets di Streamlit Cloud (o nel file .streamlit/secrets.toml).
try:
    _autore = st.secrets.get("AUTORE_APP", "") or ""
except Exception:
    _autore = ""
if not _autore:
    try:
        import os as _os
        import tomllib as _tomllib
        _p = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                           ".streamlit", "secrets.toml")
        if _os.path.exists(_p):
            with open(_p, "rb") as _f:
                _autore = str((_tomllib.load(_f) or {}).get("AUTORE_APP", "")
                              or "").strip()
    except Exception:
        _autore = ""
if _autore:
    AUTORE_APP = _autore.strip()

# "versione" = VERSION.txt (commit) + data del file piu' recente
# (cosi' si vede subito se l'app online gira il codice giusto)
BUILD = hotreload.versione()

st.set_page_config(
    page_title="CANTICO - Dalla Parola alla Lode",
    page_icon="🎵",
    layout="centered",
    initial_sidebar_state="collapsed",
)

_SCRIPT_UID = """
<script>
(function () {
  try {
    var m = document.cookie.match(/(^|;\\s*)cantico_uid=([^;]+)/);
    if (!m) {
      var id = "";
      try {
        if (window.crypto && window.crypto.randomUUID) {
          id = window.crypto.randomUUID().replace(/-/g, "");
        }
      } catch (e) {}
      if (!id) {
        id = Date.now().toString(16) + Math.random().toString(16).slice(2, 10);
      }
      document.cookie = "cantico_uid=" + id + "; path=/; max-age=31536000; SameSite=Lax";
    }
  } catch (e) {}
})();
</script>
"""

# eseguo lo script: il browser salva l'id dell'utente nel cookie
html(_SCRIPT_UID, js=True)

CSS = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

  .block-container { padding: 1rem 0.9rem 5rem 0.9rem; max-width: 780px; }
  h1, h2, h3, h4 { font-family: 'Inter', system-ui, -apple-system, sans-serif !important; letter-spacing: -0.02em; }
  h1 { font-size: 1.7rem !important; line-height: 1.2; font-weight: 700 !important; }
  .stApp p, .stApp label, .stApp li { font-family: 'Inter', system-ui, -apple-system, sans-serif; }
  /* NB: NON forzare il font sugli <span>: conterrebbero le icone Material di
     Streamlit, che verrebbero mostrate come testo spazzatura. */
  [data-testid="stMarkdownContainer"] { font-family: 'Inter', system-ui, -apple-system, sans-serif; }

  /* pulsanti grandi e "tap friendly" da telefono */
  .stButton > button, .stLinkButton > a {
      min-height: 50px; border-radius: 14px; font-weight: 700; font-size: 1rem;
      border: none !important; box-shadow: 0 4px 14px rgba(15,23,42,.16);
      display: flex; align-items: center; justify-content: center; gap: 6px;
      transition: transform .12s ease, filter .12s ease;
  }
  .stButton > button:hover, .stLinkButton > a:hover { transform: translateY(-1px); filter: brightness(1.06); }
  .stButton > button:active, .stLinkButton > a:active { transform: translateY(1px); }

  .stTextArea textarea {
      font-size: 1.05rem; line-height: 1.6; border-radius: 14px; padding: 14px;
      min-height: 160px; font-family: 'Inter', system-ui, sans-serif;
  }
  .stTextInput input { font-size: 1rem; border-radius: 12px; min-height: 48px; }
  div[data-baseweb="select"] > div { min-height: 50px; border-radius: 12px; }

  .hero {
      background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 55%, #db2777 100%);
      color: #fff; border-radius: 20px; padding: 18px; margin-bottom: 12px;
      box-shadow: 0 8px 24px rgba(109,40,217,.22);
  }
  .hero h1 { color: #fff !important; margin: 0 0 4px 0 !important; }
  .hero p  { color: rgba(255,255,255,.93) !important; margin: 0 !important; font-size: .95rem !important; }

  .step {
      display: inline-block; background: #4f46e5; color: #fff; border-radius: 999px;
      padding: 3px 12px; font-size: .78rem; font-weight: 700; margin-bottom: 4px;
  }
  .badge {
      display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: .75rem;
      font-weight: 700; background: #eef2ff; color: #4338ca; margin-bottom: 6px;
  }
  .card-title { font-weight: 700; font-size: 1.02rem; line-height: 1.35; color: inherit; }
  .card-meta  { font-size: .82rem; opacity: .72; margin-top: 3px; }
  .thumb { width: 104px; border-radius: 10px; flex-shrink: 0; }
  .chip {
      display: inline-block; padding: 4px 11px; border-radius: 999px; font-size: .8rem;
      background: #ecfdf5; color: #047857; font-weight: 600; margin: 0 6px 6px 0;
  }
  /* le parole chiave: una dopo l'altra, con lo spazio TRA una e l'altra */
  .chips { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 4px; }
  .chips .chip { margin: 0; }
  /* il campo "trucco" che serve solo a far ricalcolare la pagina:
     non deve essere visibile */
  div[data-testid="stTextInput"]:has(input[placeholder="_cantico_trigger"]) {
      display: none !important;
  }
  .box {
      background: #f8fafc; border-left: 4px solid #7c3aed; border-radius: 10px;
      padding: 11px 13px; font-size: .88rem; word-break: break-word; line-height: 1.55;
  }
  .box-ok   { background: #f0fdf4; border-left-color: #16a34a; }
  .box-warn { background: #fffbeb; border-left-color: #f59e0b; }
  .note { font-size: .84rem; opacity: .78; line-height: 1.6; }
  .copybtn {
      width: 100%; min-height: 48px; border: none; border-radius: 14px;
      background: linear-gradient(135deg, #4f46e5, #7c3aed); color: #fff;
      font-weight: 700; font-size: .97rem; cursor: pointer;
      font-family: 'Inter', system-ui, -apple-system, sans-serif;
      box-shadow: 0 4px 14px rgba(79,70,229,.28);
  }
  .copybtn:active { transform: translateY(1px); }
  .timeline { font-size: .87rem; line-height: 1.9; }
  hr { margin: 1.3rem 0; opacity: .3; }

  @media (max-width: 640px) {
      h1 { font-size: 1.45rem !important; }
      .hero { padding: 15px; border-radius: 16px; }
      .thumb { width: 86px; }
      .stButton > button, .stLinkButton > a { min-height: 48px; font-size: .94rem; }
  }
</style>
"""
html(CSS + SCRIPT_COPIA, js=True)


# --------------------------------------------------------------------------
# Helper
# --------------------------------------------------------------------------

def esc(testo: str) -> str:
    return html_mod.escape(testo or "", quote=True)


def _js_string(testo: str) -> str:
    return json.dumps(testo, ensure_ascii=False).replace("</", "<\\/")


# Salva la chiave Treblo nel BROWSER (come quella Gemini): resta privata,
# non finisce sul server e non consuma i crediti degli altri.
_SCRIPT_SALVA_TREBLO = """
<script>
(function () {
  try {
    localStorage.setItem("cantico_chiave_treblo", "__CHIAVE__");
  } catch (e) {}
})();
</script>
"""

_SCRIPT_LEGGI_TREBLO = """
<script>
(function () {
  try {
    if (window.__canticoTrebloMesso) return;
    window.__canticoTrebloMesso = true;
    function prova() {
      var k = localStorage.getItem("cantico_chiave_treblo");
      if (!k) return;
      var campi = document.querySelectorAll('input[type="password"]');
      for (var i = 0; i < campi.length; i++) {
        var lab = campi[i].closest('div[data-testid="stTextInput"]');
        if (lab && /Chiave Treblo/i.test(lab.textContent || lab.innerText || "")) {
          if (campi[i].value) return;
          var proto = Object.getPrototypeOf(campi[i]);
          var setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
          setter.call(campi[i], k);
          campi[i].dispatchEvent(new Event('input', { bubbles: true }));
          return;
        }
      }
      setTimeout(prova, 300);
    }
    setTimeout(prova, 100);
  } catch (e) {}
})();
</script>
"""

# Salva la chiave Gemini nel BROWSER di chi la inserisce (localStorage):
# resta privata, non finisce sul server e non consuma la quota degli altri.
_SCRIPT_SALVA_CHIAVE = """
<script>
(function () {
  try {
    localStorage.setItem("cantico_chiave_gemini", "__CHIAVE__");
  } catch (e) {}
})();
</script>
"""

# Riempi il campo "Chiave Google Gemini" con la chiave salvata nel browser.
# NB: si riempie UNA volta sola per pagina: se lo rifacessimo a ogni rerun,
# l'evento 'input' rilancierebbe l'app all'infinito.
_SCRIPT_LEGGI_CHIAVE = """
<script>
(function () {
  try {
    if (window.__canticoGeminiMesso) return;
    window.__canticoGeminiMesso = true;
    function prova() {
      var k = localStorage.getItem("cantico_chiave_gemini");
      if (!k) return;
      var campi = document.querySelectorAll('input[type="password"]');
      for (var i = 0; i < campi.length; i++) {
        var lab = campi[i].closest('div[data-testid="stTextInput"]');
        if (lab && /Chiave Google Gemini/i.test(lab.textContent || lab.innerText || "")) {
          if (campi[i].value) return;
          var proto = Object.getPrototypeOf(campi[i]);
          var setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
          setter.call(campi[i], k);
          campi[i].dispatchEvent(new Event('input', { bubbles: true }));
          return;
        }
      }
      setTimeout(prova, 300);
    }
    setTimeout(prova, 100);
  } catch (e) {}
})();
</script>
"""


def _esc_attr(testo: str) -> str:
    """Testo pronto per un attributo HTML (escape di &, <, >, ")."""
    return (testo.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _parole_chiave_pulite(parole, numero: int = 3) -> list[str]:
    """
    Le parole chiave sempre separate e leggibili.

    Se l'IA le scrive attaccate ("Lodefedeadorazione") le si divide; se le
    scrive con virgole o spazi le si separa. Servono cosi' anche alla ricerca
    della canzone: una parola sola e' un termine che YouTube non trova.
    """
    _out: list[str] = []
    for _p in (parole or []):
        for _q in re.split(r"[,;|·•\n\t]+|\s{2,}", str(_p).strip()):
            _q = _q.strip(" .*-")
            if 2 < len(_q) < 30 and _q.lower() not in [x.lower() for x in _out]:
                _out.append(_q)
            if len(_out) >= numero:
                return _out
    return _out


def _md(testo: str) -> str:
    """
    Testo dell'IA pronto per l'HTML: scappa tutto e trasforma il grassetto
    markdown (**parola**) in <b>parola</b>, cosi' i titoli delle sezioni si
    vedono come titoli e non come due stelline.
    """
    t = esc(testo or "")
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t, flags=re.S)
    t = re.sub(r"(?<![\w*])\*([^*\n]{1,80})\*(?![\w*])", r"<i>\1</i>", t)
    return t


def blocco_copia(testo: str, chiave: str,
                 etichetta: str = "\U0001F4CB Copia Titolo") -> None:
    """
    Bottone che copia il testo negli appunti.

    NESSUNA iframe: dentro Streamlit Cloud (che avvolge l'app in una iframe)
    le iframe annidate facevano crashare il frontend React
    ("NotFoundError: removeChild ... not a child of this node").
    Qui si usa un handler inline: funziona anche se il markup viene inserito
    via innerHTML, e la copia usa la Clipboard API (con fallback execCommand).
    """
    _label = _esc_attr(etichetta)
    _dati = _esc_attr(testo)
    html(
        f'<button class="copybtn" data-copy="{_dati}" data-label="{_label}">'
        f'{etichetta}</button>'
    )


def embed_youtube(video_id: str) -> None:
    """Anteprima: apre il video su YouTube (niente iframe, niente crash React)."""
    st.link_button(
        "\U0001F3A7 Ascolta l'anteprima su YouTube",
        f"https://www.youtube.com/watch?v={video_id}",
        use_container_width=True,
    )


DURATA_MAX_SEC = 420          # 7 minuti: scarto compilazioni e culti
DURATA_MAX_BIBLIA_SEC = 1800    # 30 minuti: per le spiegazioni/prediche


@st.cache_data(ttl=1800, show_spinner=False)
def ricerca_cached(query_list: tuple[str, ...], n: int,
                   parole_chiave: tuple[str, ...],
                   max_durata: int = DURATA_MAX_SEC,
                   escludi: tuple[str, ...] = (),
                   offset: int = 0,
                   riferimento: str = "") -> list:
    return ricerca_multipla(list(query_list), max_risultati=n,
                            parole_chiave=list(parole_chiave),
                            max_durata=max_durata,
                            escludi=list(escludi),
                            offset=offset,
                            riferimento=riferimento)


@st.cache_data(ttl=1800, show_spinner=False)
def ricerca_tiktok_cached(query: str, n: int) -> list:
    return cerca_suoni_tiktok(query, max_risultati=n)


@st.cache_data(ttl=3600, show_spinner=False)
def cerca_versetti_cached(testo: str, n: int) -> list:
    """
    Cerca i versetti biblici piu' adatti a un pensiero.

    Se il testo contiene un RIFERIMENTO esatto (es. "Salmo 23,1", oppure
    "Cantico dei Cantici 8,7"), quello va IN CIMA: e' il versetto che hai
    chiesto tu, non uno trovato a caso per le parole.
    """
    _esatti = []
    try:
        _rif = rileva_riferimento(testo or "")
    except Exception:
        _rif = None
    if _rif and _rif.get("versetto"):
        try:
            _v = trova_versetto(_rif["libro"], _rif["capitolo"],
                                _rif["versetto"],
                                versetto_fine=_rif.get("versetto_fine"))
        except Exception:
            _v = None
        if _v:
            _v = dict(_v)
            _v["esatto"] = True
            _v.setdefault("temi", [])
            _esatti.append(_v)
    _resto = cerca_versetti(testo, n)
    if _esatti:
        _gia = {v.get("riferimento") for v in _esatti}
        _resto = [v for v in _resto if v.get("riferimento") not in _gia]
    return (_esatti + _resto)[:max(n, len(_esatti))]


def _imposta_testo(testo: str) -> None:
    """Callback: mette il testo scelto nella casella di input e avvia la ricerca."""
    st.session_state["testo_input"] = testo
    st.session_state["correzione"] = None
    st.session_state["_cerca_subito"] = True




def hashtag_str(hashtag: list[str] | None) -> str:
    """Gli hashtag in una riga (per la caption)."""
    return " ".join(h or [] for h in (hashtag or []))



# Lo script che mette il cookie "cantico_uid": e' l'identita' del browser,
# cosi' ogni utente ha i SUOI post, le SUE canzoni, il SUO archivio,
# senza dover scrivere nessun codice.


def _id_utente() -> str:
    """
    L'identita' di chi sta usando l'app: un codice automatico nel cookie
    del browser. Ogni persona ha cosi' i suoi post e le sue cose, senza
    dover configurare niente.
    """
    _cookie = ""
    try:
        _cookie = str(st.context.cookies.get("cantico_uid", "") or "").strip()
    except Exception:
        _cookie = ""
    if _cookie:
        if st.session_state.get("uid_utente") != _cookie:
            st.session_state["uid_utente"] = _cookie
            st.session_state["archivio"] = carica_archivio(_cookie)
        return _cookie
    _sessione = st.session_state.get("uid_utente")
    if not _sessione:
        import uuid as _uuid
        _sessione = _uuid.uuid4().hex[:16]
        st.session_state["uid_utente"] = _sessione
    return _sessione


def _riferimento_breve(rif: dict) -> str:
    """Es. {'libro': 'Salmi', 'capitolo': 23} -> 'Salmo 23' (forma YouTube)."""
    libro = (rif.get("libro") or "").strip()
    if libro.lower().startswith("sal"):
        libro = "Salmo"
    cap = rif.get("capitolo")
    return f"{libro} {cap}".strip()


def _riferimento_corrente() -> dict:
    """Il riferimento biblico attivo (per lo studio o quello forzato)."""
    _st = st.session_state.get("versetto_studio") or {}
    _rif = _st.get("riferimento") or {}
    if _rif:
        return _rif
    return st.session_state.get("riferimento_forzato") or {}


def _direzione_musicale(interpretazione: str) -> str:
    """
    Ricava dall'INTERPRETAZIONE la direzione musicale per la ricerca:
    il tono (lento, di vittoria, di consolazione...) e il tema.

    Cosi' la ricerca delle canzoni non usa parole generiche, ma quelle
    che l'IA (o lo studio) ha ricavato dal versetto.
    """
    testo = (interpretazione or "").strip()
    if not testo:
        return ""
    _parti: list[str] = []

    # 1) il tono: dalla sezione "PER LA LODE"
    _lode = ""
    _up = testo.upper()
    for _marcatore in ("PER LA LODE", "5. PER LA LODE", "DALLA VOCE DI DIO"):
        _i = _up.find(_marcatore)
        if _i >= 0:
            _lode = testo[_i + len(_marcatore):_i + len(_marcatore) + 700]
            break
    if _lode:
        # parole che dicono COME cantare
        _termini = {
            "lento": "lento", "lenta": "lento", "lento": "lento",
            "dolce": "dolce", "calmo": "calmo", "calma": "calmo",
            "commosso": "commosso", "commossa": "commosso",
            "vittoria": "vittoria", "trionfo": "trionfo", "celebre": "celebre",
            "allegro": "allegro", "gioioso": "gioioso", "gioia": "gioia",
            "consolazione": "consolazione", "confidenza": "confidenza",
            "fiducia": "fiducia", "coraggio": "coraggio", "amore": "amore",
            "adorazione": "adorazione", "lode": "lode", "speme": "speranza",
            "speranza": "speranza", "gridare": "grido", "esultazione": "esultazione",
        }
        _basso = _lode.lower()
        for _k, _v in _termini.items():
            if _k in _basso and _v not in _parti:
                _parti.append(_v)
            if len(_parti) >= 2:
                break

    # 2) il mood del testo (adorazione profonda, inno di vittoria...)
    try:
        from text_tools import rileva_mood
        _mood = rileva_mood(testo)
        if _mood:
            for _p in (_mood.get("parole") or [])[:2]:
                if _p and _p not in _parti:
                    _parti.append(_p)
    except Exception:
        pass

    return " ".join(_parti[:3])


def _chiave_gemini_attiva() -> str:
    """
    La chiave Gemini che vale davvero, in ordine di priorita':
      1) quella incollata nel WIZARD (quella dell'utente)
      2) quella salvata nel SUO browser (cookie): la sua, non del server
      3) quella nei secrets di Streamlit / nel file locale
      4) quella ricordata sul server (per tutti gli utenti)
    """
    for _k in ("cfg_gemini", "chiave_gemini"):
        _v = str(st.session_state.get(_k, "") or "").strip()
        if _v:
            return _v
    # la chiave dell'utente, salvata nel suo browser
    try:
        _v = str((chiavi_browser() or {}).get("gemini", "") or "").strip()
        if _v:
            return _v
    except Exception:
        pass
    return (chiave_gemini_da_secrets() or "").strip()


def _chiedi_ia(prompt: str, chiave_gemini: str = "",
               chiave_openai: str = "") -> dict:
    """
    Chiede l'interpretazione all'IA migliore disponibile, in ordine:
      1) Google Gemini  (se hai la chiave: la qualita' migliore E veloce)
      2) ChatGPT API    (se hai la chiave OpenAI: veloce anche lui)
      3) IA gratuita senza chiave (sempre disponibile, ma LENTA: e' l'ultima
         risorsa, non la prima, cosi' con la chiave Gemini non si aspetta)
    Ogni risposta viene controllata: se e' "rotta" (italiano sbagliato)
    si passa al servizio successivo.
    Non solleva mai: se fallisce tutto, torna un errore e l'app usa il
    motore di studio.
    """
    _problemi: list[str] = []

    if chiave_gemini:
        _r = interpreta_gemini(prompt, chiave=chiave_gemini)
        if _r.get("testo") and qualita_ia(_r["testo"]):
            return _r
        _problemi.append("Gemini: " + (_r.get("errore") or "risposta non "
                                                            "utilizzabile"))
    else:
        _problemi.append("Gemini: nessuna chiave")

    # OpenAI PRIMA della IA gratuita: e' una chiamata normalissima, mentre
    # la gratuita deve aspettare ~30 secondi tra un tentativo e l'altro.
    if chiave_openai:
        _r = interpreta_con_ia(prompt, chiave=chiave_openai)
        if _r.get("testo") and qualita_ia(_r["testo"]):
            return _r
        _problemi.append("OpenAI: " + (_r.get("errore") or
                                        "risposta non utilizzabile"))

    # ultima risorsa: la IA gratuita (1 solo tentativo: se e' occupata l'app
    # va avanti col motore di studio invece di aspettare un minuto)
    _r = interpreta_gratis(prompt, tentativi=1)
    if _r.get("testo") and qualita_ia(_r["testo"]):
        return _r
    _problemi.append("IA gratuita: " + (_r.get("errore") or
                                        "risposta non utilizzabile"))

    return {"testo": "", "parole_chiave": [], "modello": "", "fonte": "IA",
            "errore": " | ".join(_problemi)}


def _post_completo(_post_ia: dict) -> str:
    """Tutto il post in un unico testo (per copiarlo con un tocco)."""
    _parti = []
    if _post_ia.get("hook"):
        _parti.append("TESTO A SCHERMO:\n" + _post_ia["hook"])
    if _post_ia.get("corpo"):
        _parti.append("DA DIRE:\n" + "\n".join(_post_ia["corpo"]))
    if _post_ia.get("caption"):
        _parti.append("CAPTION:\n" + _post_ia["caption"])
    if _post_ia.get("cta"):
        _parti.append("INVITO:\n" + _post_ia["cta"])
    _m = _post_ia.get("momento") or {}
    if _m.get("giorno"):
        _parti.append(f"QUANDO: {_m.get('giorno','')} - "
                      f"{_m.get('fascia','')} ({_m.get('orario','')})")
    return "\n\n".join(_parti)


def _mostra_post_ia(_post_ia: dict, suffisso: str = "ia") -> None:
    """Mostra il post ridotto dall'IA (hook, script, caption, CTA)."""
    if not (_post_ia.get("hook") or _post_ia.get("caption")):
        return
    html(
        '<div class="step">IL POST TIKTOK</div>'
        '<div class="note">La riflessione ridotta: quello che appare a '
        'schermo e quello che dici. Copi quello che vuoi, o tutto in un '
        'colpo con "Copia tutto il post".</div>')
    with st.container(border=True):
        blocco_copia(_post_completo(_post_ia), f"copia_tutto_{suffisso}",
                     "\U0001F4CB Copia tutto il post")
        html('<div class="badge" style="margin-top:8px">TESTO A SCHERMO '
             '(0-3 secondi)</div>'
             f'<div class="card-title">{esc(_post_ia.get("hook", ""))}</div>')
        blocco_copia(_post_ia.get("hook", ""), f"copia_hook_{suffisso}",
                     "\U0001F4CB Copia il testo a schermo")
        if _post_ia.get("corpo"):
            _n_righe = len(_post_ia.get("corpo", []))
            html(f'<div class="badge" style="margin-top:8px">IL TESTO DA '
                 f'DIRE ({_n_righe} righe, da leggere ad alta voce)</div>')
            for _riga in _post_ia.get("corpo", []):
                html(f'<div class="note">&bull; {esc(_riga)}</div>')
            blocco_copia("\n".join(_post_ia.get("corpo", [])),
                         f"copia_corpo_{suffisso}",
                         "\U0001F4CB Copia lo script da dire")
        if _post_ia.get("caption"):
            html('<div class="badge" style="margin-top:8px">CAPTION</div>'
                 f'<div class="card-title">{esc(_post_ia.get("caption",""))}'
                 '</div>')
            blocco_copia(_post_ia.get("caption", ""), f"copia_caption_{suffisso}",
                         "\U0001F4CB Copia la caption")
        if _post_ia.get("cta"):
            html(f'<div class="note">Invito: {esc(_post_ia.get("cta",""))}'
                 '</div>')
        # ---- IL MOMENTO GIUSTO PER PUBBLICARE ----
        _mom = _post_ia.get("momento") or {}
        if _mom.get("giorno"):
            html(
                '<div class="badge" style="margin-top:8px">QUANDO PUBBLICARE'
                '</div>'
                f'<div class="card-title">{esc(_mom.get("giorno",""))} &mdash; '
                f'{esc(_mom.get("fascia",""))} ({esc(_mom.get("orario",""))})'
                '</div>'
                f'<div class="note">{esc(_mom.get("motivo",""))}</div>')
            if _mom.get("consiglio"):
                html(f'<div class="note"><b>Consiglio:</b> '
                     f'{esc(_mom.get("consiglio",""))}</div>')


def _salva_riflessione_ia(riflessione: str, post: dict, parole_chiave=None,
                          fonte: str = "IA") -> dict:
    """Mette in stato la riflessione e il post, e azzera il campo modificabile."""
    _esito = {
        "riflessione": (riflessione or "").strip(),
        "parole_chiave": list(parole_chiave or []),
        "post": post or {},
        "fonte": fonte,
    }
    st.session_state["riflessione_ia"] = _esito
    st.session_state.pop("riflessione_ia_testo", None)
    return _esito


def _rigenera_riflessione(testo_versetto: str, interpretazione: str,
                          riferimento: str) -> dict:
    """Chiede all'IA la riflessione + la riduzione per il post TikTok."""
    _esito = genera_riflessione_e_post(
        testo_versetto=testo_versetto,
        interpretazione=interpretazione,
        riferimento=riferimento,
        chiave_gemini=_chiave_gemini_attiva(),
        chiave_openai=st.session_state.get("chiave_ia", ""))
    st.session_state["riflessione_ia"] = _esito
    st.session_state.pop("riflessione_ia_testo", None)
    return _esito


def _studia_versetto() -> None:
    """
    FASE 1: interpretazione dottrinale pentecostale del versetto
            (esposizioni/predicazioni reali + parole chiave spirituali)
    FASE 2: ricerca musicale forzata = [riferimento] + [3 parole chiave]
            + filtro pentecostale + parole negative.
    """
    testo = st.session_state.get("testo_input", "") or ""

    # 1) se l'utente ha scelto un ambito (versetto / capitolo / intervallo)
    #    uso QUELLO, non quello digitato
    riferimento = st.session_state.get("riferimento_forzato")
    if not riferimento:
        riferimento = rileva_riferimento(testo)

    # 2) l'utente puo' scegliere QUANTI versetti studiare (es. "18-21")
    _sotto = (st.session_state.get("sotto_passaggio") or "").strip()
    if riferimento and _sotto:
        _r2 = rileva_riferimento(
            f"{riferimento['libro']} {riferimento['capitolo']} {_sotto}")
        if _r2 and _r2.get("versetto"):
            riferimento = _r2

    if not riferimento:
        st.session_state["versetto_studio"] = {"errore": (
            "Non riconosco un riferimento biblico. Scrivilo cosi': "
            "Giovanni 3,16  oppure  Salmo 23:1")}
        return

    versetto = trova_versetto(riferimento["libro"], riferimento["capitolo"],
                               riferimento["versetto"] or 1,
                               versetto_fine=riferimento.get("versetto_fine"))
    if not versetto:
        st.session_state["versetto_studio"] = {"errore": (
            f"Non trovo {riferimento['riferimento']} nel testo biblico.")}
        return

    # testo da studiare:
    #  - solo il capitolo ("Salmo 23")  -> tutto il capitolo
    #  - un intervallo ("Marco 12,28-31") -> tutto il passaggio
    #  - un versetto singolo -> il versetto
    testo_intero = versetto["testo_pulito"]
    if not riferimento.get("versetto"):
        capitolo = versetto.get("capitolo_versetti", [])
        testo_intero = " ".join(c["testo"] for c in capitolo)
        versetto["testo_capitolo"] = testo_intero
        versetto["e_capitolo_intero"] = True
    elif versetto.get("testo_passaggio"):
        testo_intero = versetto["testo_passaggio"]
        versetto["e_capitolo_intero"] = True

    # se l'utente ha scelto UN versetto del passaggio, studio solo quello
    _scelta = st.session_state.get("verso_selezionato")
    if _scelta:
        try:
            _num = int(_scelta[1])
            _singolo = trova_versetto(riferimento["libro"],
                                      riferimento["capitolo"], _num)
            if _singolo:
                versetto = _singolo
        except Exception:
            pass

        # --- FASE 1: solo lo studio del versetto (niente ricerca YouTube) ---
    interpretazioni = []
    versetto["trascrizione"] = None
    analisi = st.session_state.get("analisi") or {}
    temi = analisi.get("temi") or ["Salvezza"]
    # se l'utente ha scelto di studiare SOLO un versetto, l'interpretazione
    # non deve citare i versetti vicini (scope = solo il versetto richiesto)
    _solo_versetto = bool(riferimento.get("versetto")) and not \
        riferimento.get("versetto_fine")
    analisi = st.session_state.get("analisi") or {}
    temi = analisi.get("temi") or ["Salvezza"]
    # se l'utente ha scelto di studiare SOLO un versetto, l'interpretazione
    # non deve citare i versetti vicini (scope = solo il versetto richiesto)
    _solo_versetto = bool(riferimento.get("versetto")) and not \
        riferimento.get("versetto_fine")
    interpretazione = interpretazione_dotrinale(
        versetto, temi[0], estrai_parole_chiave(testo_intero, 4),
        includi_contesto=not _solo_versetto)

    # --- INTERPRETAZIONE CON IA GRATUITA (predefinita) ---
    # Il motore di studio e' il ripiego: se l'IA gratuita risponde, l'interpretazione
    # e' scritta sul TUO versetto (e quindi diversa per ogni passaggio).
    if st.session_state.get("usa_ia_gratuita", True):
        _prompt = PROMPT_INTERPRETAZIONE.format(
            riferimento=riferimento.get("riferimento", ""),
            testo_versetto=(versetto.get("testo_pulito", "") + "\n\n"),
        )
        with st.spinner("\U0001F9E0 Sto scrivendo l'interpretazione del tuo "
                        "versetto (come un maestro della Scrittura)..."):
            _ris_ia = _chiedi_ia(
                _prompt,
                chiave_gemini=_chiave_gemini_attiva(),
                chiave_openai=st.session_state.get("chiave_ia", ""))
        if _ris_ia.get("testo"):
            # le parole chiave che scrive l'IA stessa guidano la ricerca
            # della canzone: cosi' la canzone e' legata all'interpretazione
            _kw_ia = parole_chiave_dall_ia(_ris_ia["testo"], 3)
            if not _kw_ia:
                _kw_ia = estrai_parole_chiave_spirituali(_ris_ia["testo"])[:3]
            interpretazione = {
                "testo": _ris_ia["testo"],
                "parole_chiave": _kw_ia,
                "fonte": _ris_ia.get("fonte", "IA"),
                "riferimento": riferimento.get("riferimento", ""),
            }
            st.session_state["ia_note"] = _ris_ia.get("nota", "")
        else:
            st.session_state["ia_note"] = _ris_ia.get("errore", "")

    # --- FASE 1b: la RIFLESSIONE + il POST TIKTOK, scritti dall'IA ---
    # Se l'utente ha lasciato attivo l'interruttore, l'app fa da sola il
    # passo dopo l'interpretazione: la riflessione personale sul versetto e
    # la sua riduzione in un post pronto per TikTok.
    if st.session_state.get("auto_riflessione", True):
        with st.spinner("\U0001F9E0 Scrivo la riflessione e la riduco per "
                        "TikTok..."):
            _rigenera_riflessione(
                testo_versetto=(versetto.get("testo_pulito", "") or ""),
                interpretazione=(interpretazione.get("testo", "") or ""),
                riferimento=riferimento.get("riferimento", ""))

    # --- FASE 1b: la RIFLESSIONE + il POST TIKTOK, scritti dall'IA ---
    # (la ricerca delle canzoni YouTube e' stata tolta: l'app genera la
    # sua canzone originale, e il post si prepara qui)
    # --- FASE 2: la ricerca delle canzoni, GUIDATA dall'interpretazione ---
    # Le parole chiave vengono dall'interpretazione (quindi dalla IA o dallo
    # studio): la canzone proposta parla davvero di quel versetto.
    parole_spirituali = interpretazione["parole_chiave"][:3]
    if not parole_spirituali:
        parole_spirituali = ["fede", "lode", "consolazione"]
    rif_breve = _riferimento_breve(riferimento)

    # la DIREZIONE musicale: la ricavo dall'interpretazione stessa
    # (tempo, atmosphere, tema che l'IA ha indicato in "PER LA LODE")
    _direzione = _direzione_musicale(interpretazione.get("testo", ""))
    query = costruisci_query_musica(rif_breve, parole_spirituali, _direzione)

    try:
        risultati = ricerca_cached(tuple(query), 15, tuple(parole_spirituali),
                                    DURATA_MAX_SEC, riferimento=rif_breve)
    except Exception:
        risultati = []

    st.session_state["versetto_studio"] = {
        "riferimento": riferimento,
        "versetto": versetto,
        "interpretazione": interpretazione,
        "interpretazioni": interpretazioni,
        "query": query,
        "parole_spirituali": parole_spirituali,
        "direzione": _direzione,
    }
    st.session_state["risultati"] = risultati
    st.session_state["query_usate"] = query
    st.session_state["scelta"] = None
    st.session_state["visti"] = [r.video_id for r in risultati]
    st.session_state["quante_mostrate"] = len(risultati)
    st.session_state["studio_parole"] = list(parole_spirituali)
    st.session_state["studio_direzione"] = _direzione


# --------------------------------------------------------------------------
# Stato
# --------------------------------------------------------------------------

for chiave, valore in (
    ("risultati", []),
    ("query_usate", []),
    ("cronologia", []),
    ("scelta", None),
    ("correzione", None),
    ("analisi", None),
    ("suoni_tiktok", []),
    ("post", None),
    ("archivio", None),
    ("codice_archivio", ""),
    ("studio_risultati", []),
    ("riferimento", None),
    ("versetti", []),
    ("_cerca_subito", False),
    ("versetto_studio", None),
    ("visti", []),
    ("quante_mostrate", 0),
    ("studio_parole", []),
    ("canzone_testi", ""),
    ("canzone_audio", ""),
    ("canzone_video", ""),
    ("suno_protegto", False),
    ("riflessione_ia", None),
    ("auto_riflessione", True),
):
    if chiave not in st.session_state:
        st.session_state[chiave] = valore

# l'archivio appartiene a chi sta usando l'app (id automatico dal cookie).
# il "codice archivio" manuale, se impostato, ha la precedenza: serve per
# ritrovare i propri post anche su un altro telefono.
_ID_UTENTE = _id_utente()
_CHIAVE_ARCHIVIO = (st.session_state.get("codice_archivio") or "").strip() \
    or _ID_UTENTE
if st.session_state.get("archivio") is None:
    st.session_state["archivio"] = carica_archivio(_CHIAVE_ARCHIVIO)



# --------------------------------------------------------------------------
# ACCESSO: password + pagina di benvenuto
# --------------------------------------------------------------------------

def _sha(testo: str) -> str:
    return hashlib.sha256((testo or "").encode("utf-8")).hexdigest()


def _segreto(nome: str, default: str = "") -> str:
    """Legge un segreto di Streamlit senza rompere nulla se manca il file."""
    try:
        return str(st.secrets.get(nome, default) or default).strip()
    except Exception:
        return default


def _hash_salvato_nel_browser() -> str:
    """
    L'hash della password che l'utente ha scelto, salvato nel SUO browser
    (il JS lo mette in un cookie, cosi' l'app puo' confrontarlo).

    Serve per la COPIA PUBBLICA dell'app: chi riceve il codice imposta
    himself la password della sua app, e da quel momento l'app e' sua.
    """
    try:
        return str(st.context.cookies.get("cantico_hash", "") or "").strip().lower()
    except Exception:
        return ""


def _password_attesa() -> str:
    """L'hash della password dalle secrets (Cloud), dall'ambiente, dal file
    locale .streamlit/secrets.toml o dal modulo accesso.py del progetto."""
    try:
        v = st.secrets.get("APP_PASSWORD_SHA256", "")
        if v:
            return str(v).strip().lower()
    except Exception:
        pass
    v = (os.environ.get("APP_PASSWORD_SHA256") or "").strip().lower()
    if v:
        return v
    # 3) modulo accesso.py del progetto (c contiene solo l'hash SHA-256)
    try:
        from accesso import PASSWORD_SHA256
        if PASSWORD_SHA256:
            return PASSWORD_SHA256.strip().lower()
    except Exception:
        pass
    try:
        import re as _re
        percorso = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               ".streamlit", "secrets.toml")
        if os.path.exists(percorso):
            testo = open(percorso, encoding="utf-8").read()
            m = _re.search(r'APP_PASSWORD_SHA256\s*=\s*"([^"]+)"', testo)
            if m:
                return m.group(1).strip().lower()
    except Exception:
        pass
    # 5) la password che l'utente ha scelto in QUESTO browser
    return _hash_salvato_nel_browser()


# lo script che porta l'hash della password dal localStorage al cookie
# (cosi' l'app puo' leggerlo e chiedere la password al rientro).
# Se il cookie non c'era ancora, tocca il campo "trucco": la pagina si
# ricalcola e l'app mostra subito la richiesta della password.
_SCRIPT_ACCESSO = """
<script>
(function () {
  try {
    if (window.__canticoAccessoMesso) return;
    window.__canticoAccessoMesso = true;
    if (document.cookie.indexOf("cantico_hash=") >= 0) return;
    var h = localStorage.getItem("cantico_accesso_hash");
    if (!h) return;
    document.cookie = "cantico_hash=" + h + "; path=/; max-age=31536000; SameSite=Lax";
    // faccio ricalcolare la pagina: cosi' l'app vede subito il cookie
    var tr = document.querySelector('input[placeholder="_cantico_trigger"]');
    if (tr) {
      var proto = Object.getPrototypeOf(tr);
      var setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
      setter.call(tr, String(Date.now()));
      tr.dispatchEvent(new Event('input', { bubbles: true }));
    }
  } catch (e) {}
})();
</script>
"""

# lo script che salva l'hash della password scelta dall'utente
_SCRIPT_SALVA_ACCESSO = """
<script>
(function () {
  try {
    localStorage.setItem("cantico_accesso_hash", "__HASH__");
    document.cookie = "cantico_hash=" + "__HASH__" + "; path=/; max-age=31536000; SameSite=Lax";
  } catch (e) {}
})();
</script>
"""


def richiedi_accesso() -> None:
    """Mostra la pagina di benvenuto e chiede la password.
    Se non c'e' password configurata, l'app resta aperta."""
    if st.session_state.get("accesso_ok"):
        return

    attesa = _password_attesa()
    if not attesa:
        # --- NESSUNA PASSWORD CONFIGURATA: chi apre imposta la sua ---
        html(_SCRIPT_ACCESSO, js=True)
        # il campo "trucco": serve solo a far ricalcolare la pagina quando
        # il browser aveva gia' una password salvata
        st.text_input("", placeholder="_cantico_trigger",
                      label_visibility="collapsed", key="_acc_trigger")
        st.markdown(
            """
            <div class="hero">
              <h1>\U0001F3B5 CANTICO</h1>
              <p><b>Dalla Parola alla Lode.</b> Questa copia dell'app non ha
                 ancora una password: <b>impostala tu</b> e l'app diventa
                 tua (solo tu, con la tua email e le tue chiavi).</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.form("crea_accesso"):
            _pw1 = st.text_input("Scegli la password della tua app",
                                 type="password",
                                 label_visibility="collapsed",
                                 placeholder="Scegli la password (6+ caratteri)")
            _pw2 = st.text_input("Ripeti la password", type="password",
                                 label_visibility="collapsed",
                                 placeholder="Ripeti la password")
            crea = st.form_submit_button("Crea la mia app", use_container_width=True)
        if crea:
            if len((_pw1 or "").strip()) < 6:
                st.error("La password deve avere almeno 6 caratteri.")
            elif _pw1 != _pw2:
                st.error("Le due password non coincidono.")
            else:
                _h = _sha(_pw1.strip())
                st.session_state["accesso_ok"] = True
                st.session_state["accesso_creato"] = True
                # NB: niente st.rerun() qui: altrimenti lo script che salva
                # la password verrebbe rimosso prima di girare nel browser.
                html(_SCRIPT_SALVA_ACCESSO.replace("__HASH__", _h), js=True)
                st.success("\u2705 La tua app e\' pronta! La password e\' stata "
                           "salvata in questo browser: da ora in poi te la "
                           "chiede per entrare.")
                return
        st.markdown(
            '<div class="note" style="text-align:center;margin-top:14px;">'
            'CANTICO &bull; dalla Parola alla Lode<br>'
            'La password resta <b>nel tuo browser</b>: nessun altro la vede.'
            '</div>',
            unsafe_allow_html=True,
        )
        st.stop()

    st.markdown(
        """
        <div class="hero">
          <h1>\U0001F3B5 CANTICO</h1>
          <p><b>Dalla Parola alla Lode.</b> Per entrare ti serve la password
             che ti ha dato chi ti ha mandato questo link.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="box">
        <b>\U0001F4F1 PRIMA DI APRIRE L'APP (2 minuti, una volta sola)</b>
        <ol style="margin:6px 0 0 18px;padding:0">
          <li>Se hai gia' aperto questa pagina dal link che ti hanno mandato,
              continua pure: adesso ti chiede la password.</li>
          <li>Nel menu del browser (tre puntini su Android, l'icona di
              condivisione su iPhone) scegli
              <b>"Aggiungi alla schermata Home"</b>: da lì in poi l'app si
              apre dalla tua Home, a schermo intero, come un'app vera.</li>
          <li>Riapri l'app toccando l'icona e inserisci la password qui
              sotto.</li>
        </ol>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("login_accesso"):
        password = st.text_input("Password", type="password",
                                 label_visibility="collapsed",
                                 placeholder="Password")
        entra = st.form_submit_button("Entra", use_container_width=True)

    if entra:
        if _sha(password) == attesa:
            st.session_state["accesso_ok"] = True
            st.rerun()
        else:
            st.error("Password non corretta. Riprova (attenzione a maiuscole/minuscole).")

    st.markdown(
        '<div class="note" style="text-align:center;margin-top:14px;">'
        'CANTICO &bull; dalla Parola alla Lode<br>'
        'Testo biblico: Sacra Bibbia - Versione Riveduta 2020 (canon protestante)<br>'
        f'creato da {esc(AUTORE_APP)}'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="note" style="text-align:center;margin-top:10px;">'
        '\U0001F510 <b>L\'archivio e\' privato:</b> quello che cerchi resta '
        'solo per te.'
        '</div>',
        unsafe_allow_html=True,
    )
    st.stop()


# --------------------------------------------------------------------------
# Sidebar: interpretazione con IA (facoltativa) + spiegazione
# --------------------------------------------------------------------------

# --------------------------------------------------------------------------
# ACCESSO (prima di tutto il resto)
richiedi_accesso()


# --------------------------------------------------------------------------
# TIKTOK: l'utente ha autorizzato l'app? Allora scambio il 'code' con il
# token e lo lascio nel suo browser (non sul server).
# --------------------------------------------------------------------------
def _collega_tiktok() -> None:
    """Rileva il codice di autorizzazione e ottiene il token."""
    try:
        _params = st.query_params
    except Exception:
        return
    _code = str(_params.get("code", "") or "").strip()
    if not _code:
        return
    try:
        import tiktok_pubblica as _tk
    except Exception:
        return
    if not _tk.collegato():
        st.error("La developer app di TikTok non e' configurata su questo "
                 "server: controlla i Secrets TIKTOK_CLIENT_KEY e "
                 "TIKTOK_CLIENT_SECRET.")
        return
    with st.spinner("Collego il tuo TikTok..."):
        _ut = {
            "client_key": _tk._cookie("cantico_tk_key"),
            "client_secret": _tk._cookie("cantico_tk_secret"),
            "redirect_uri": _tk._cookie("cantico_tk_redirect"),
        }
        _ut = {k: v for k, v in _ut.items() if v}
        _r = _tk.scambia_code(_code, _ut)
    if _r.get("access_token"):
        st.session_state["tiktok_token"] = _r["access_token"]
        st.session_state["tiktok_token_scaduto"] = False
        try:
            html(_tk.SCRIPT_SALVA_TOKEN.replace(
                "__TOKEN__", _r["access_token"]), js=True)
        except Exception:
            pass
        st.success("\u2705 TikTok collegato! Ora puoi pubblicare con un "
                   "tasto.")
    else:
        st.error("TikTok non ha accettato l'autorizzazione: " +
                 str(_r.get("errore", ""))[:180])
    # pulisco l'indirizzo: il codice non deve restare nella barra
    try:
        st.query_params.clear()
    except Exception:
        pass
    st.rerun()


_collega_tiktok()


# --------------------------------------------------------------------------
# Sidebar: interpretazione con IA (facoltativa) + spiegazione
with st.sidebar:
    # ======================================================================
    # LA CARD "ATTIVA GEMINI": il primo gesto di chi apre l'app.
    # Ognuno mette la SUA chiave: resta nel suo browser, la quota e' sua,
    # nessun altro la vede e nessuno la consuma al posto suo.
    # ======================================================================
    _chiave_gia = (st.session_state.get("chiave_gemini")
                   or st.session_state.get("cfg_gemini") or "").strip()
    _server_ha_chiave = bool(chiave_gemini_da_secrets())
    # se non c'e' nessuna chiave, il WIZARD qui sopra e' l'unico posto dove
    # metterla (niente campi duplicati)
    _mostra_card = (not _chiave_gia) and (not _server_ha_chiave)
    if _mostra_card:
        st.markdown("### \u2699\uFE0F Configura la tua app (2 minuti)")
        html(
            '<div class="box"><b>Questa app si configura da sola con le '
            'TUE chiavi.</b><br>'
            'Nessuno deve prestarti niente e nessuno paga al posto tuo: '
            'basta mettere <b>la tua email</b>, scegliere <b>una password</b> '
            'e creare <b>le tue chiavi API</b> (tutte gratis).<br>'
            'L\'app te le salva <b>nel tuo browser</b>: la prossima volta le '
            'trovi gia\' li, nessun altro le vede e <b>la quota e\' tutta '
            'tua</b>.<br><br>'
            '<b>Gemini</b> (gratis) serve per scrivere l\'interpretazione e '
            'la riflessione: senza, l\'app funziona lo stesso ma piu\' '
            'lentamente.</div>')
        _setup = pannello_setup(st, html, esc)
        # le chiavi raccolte entrano subito in funzione
        if _setup.get("gemini"):
            st.session_state["cfg_gemini"] = _setup["gemini"]
            st.session_state["chiave_gemini"] = _setup["gemini"]
        if _setup.get("treblo"):
            st.session_state["chiave_treblo"] = _setup["treblo"]
        if _setup.get("hf"):
            st.session_state["token_hf"] = _setup["hf"]
        st.markdown("---")

    st.markdown("### \U0001F9E0 Interpretazione con IA")
    if _mostra_card:
        st.markdown(
            '<div class="note">L\'interpretazione la scrive un\'<b>IA che '
            'conosce la Scrittura</b>. Attivando Gemini qui sopra diventa '
            'veloce e profonda; senza chiave l\'app funziona lo stesso, ma '
            'usa la IA gratuita (piu\' lenta).<br><br>'
            '<b>Le canzoni le cerca sempre l\'app</b> (brani reali, filtro '
            'pentecostale): l\'IA non consiglia mai titoli di canzoni, ma le '
            'sue parole chiave guidano la ricerca.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div class=\"note\">L'interpretazione la scrive un'<b>IA che "
            "conosce la Scrittura</b>. Ci sono due strade:<br>"
            "<b>1)</b> <b>Google Gemini</b> (gratis, la piu' bella): metti la "
            "tua chiave qui sotto &rarr; <a href='https://aistudio.google.com/apikey' "
            "target='_blank'>aistudio.google.com/apikey</a> (ci metti un secondo, "
            "e' gratis e illimitata per l'uso quotidiano)<br>"
            "<b>2)</b> <b>IA gratuita senza chiave</b>: l'app usa subito un "
            "servizio gratuito, ma e' piu' lento e a volte occupato<br><br>"
            "C'è anche la <b>chiave API OpenAI</b>, se preferisci ChatGPT.<br><br>"
            "<b>Le canzoni le cerca sempre l'app</b> (brani reali, filtro "
            "pentecostale): l'IA non consiglia mai titoli di canzoni, ma le sue "
            "parole chiave guidano la ricerca.</div>",
            unsafe_allow_html=True,
        )
    if not _mostra_card:
        _chiave_gemini = st.text_input(
            "Chiave Google Gemini (gratis)",
            # ATTENZIONE: il campo resta VUOTO. Se ci mettessi la chiave del
            # server (quella nei Secrets del Cloud), comparirebbe nel codice
            # della pagina e ogni utente dell'app potrebbe vederla.
            # La chiave del server la usa l'app da sola, senza mostrarla.
            value="",
            type="password",
            help="La prendi gratis su aistudio.google.com/api-keys. Con questa "
                 "chiave l'interpretazione viene scritta da Gemini, con la "
                 "profondita' di un maestro della Scrittura. Se la lasci vuota, "
                 "l'app usa comunque l'IA gratuita senza chiave.",
            key="chiave_gemini",
        )
        if not chiave_gemini_da_secrets():
            # niente chiave: avviso chiaro, con il link per prenderla
            html(
                '<div class="box box-warn"><b>\u26A0\uFE0F Gemini non e\' ancora '
                'attivo</b><br>Adesso l\'app usa la <b>IA gratuita</b>: fa il suo '
                'lavoro, ma e\' piu\' lenta e la scrittura e\' meno profonda. '
                'La chiave di Google Gemini e\' <b>gratis</b> e si prende in un '
                'minuto: <a href="https://aistudio.google.com/api-keys" '
                'target="_blank">aistudio.google.com/api-keys</a> &rarr; "Create '
                'API key" &rarr; incolla qui sotto.<br>'
                'Poi scegli dove tenerla:<br>'
                '&bull; <b>"Ricorda su QUESTO dispositivo"</b> (sotto): solo per '
                'te, nel tuo browser, la quota resta tua;<br>'
                '&bull; <b>"Condividi con TUTTI"</b> (sotto): la mette sul server, '
                'cosi\' vale per tutti e per l\'app online, ma la quota e\' '
                'condivisa.</div>')
        if chiave_gemini_da_secrets():
            html(
                '<div class="note box-ok">\u2705 <b>Gemini e\' gia\' attivo</b> '
                '(chiave gia\' configurata): le interpretazioni vengono scritte '
                'da Gemini.</div>')
            html(
                '<div class="note">\U0001F517 Questa chiave e\' <b>del server</b>: '
                'la usa chiunque apra l\'app, quindi la quota gratuita la '
                'consumano tutti. Se vuoi la tua <b>solo per te</b> (e la quota '
                'intatta), metti la tua chiave qui sotto e spunta "Ricorda su '
                'QUESTO dispositivo": la tua ha la precedenza su questa.</div>')
            if st.button("\U0001F5D1 Togli la chiave da questo server",
                         use_container_width=True, key="dimentica_chiave"):
                dimentica_chiave_gemini()
                st.session_state["chiave_gemini"] = ""
                st.rerun()
            if fonte_chiave_gemini() == "secrets":
                html(
                    '<div class="note">\U0001F510 Questa chiave sta nei '
                    '<b>Secrets di Streamlit Cloud</b>: per toglierla devi '
                    'cancellarla li\' (Share.streamlit.io &rarr; la tua app '
                    '&rarr; Settings &rarr; Secrets).</div>')
        else:
            # riprendi la chiave salvata nel TUO browser (solo per te)
            html(_SCRIPT_LEGGI_CHIAVE, js=True)
            html(
                '<div class="note">\U0001F511 <b>Senza chiave l\'app funziona '
                'lo stesso</b>: usa lo studio del versetto (costruito sul testo '
                'e sulle sue immagini) e l\'IA gratuita senza chiave. Ma con una '
                'chiave Gemini gratuita l\'interpretazione diventa molto piu\' '
                'profonda, scritta come un maestro della Scrittura. '
                '<a href="https://aistudio.google.com/api-keys" '
                'target="_blank">Prendila qui</a> (ci metti un minuto).</div>')
            # La chiave si ricorda NEL BROWSER (solo per te, la quota e' tua):
            # nessun altro utente la vede e nessuno la consuma al posto tuo.
            st.checkbox(
                "Ricorda la chiave su QUESTO dispositivo (solo per me)",
                key="ricorda_dispositivo",
                help="Salva la chiave nel TUO browser (come una password salvata). "
                     "Nessun altro utente dell'app la vede, e la quota gratuita "
                     "resta tua. Non finisce MAI su GitHub ne' sul server.",
            )
            if st.session_state.get("ricorda_dispositivo") and _chiave_gemini:
                html(_SCRIPT_SALVA_CHIAVE.replace("__CHIAVE__",
                                                   _js_string(_chiave_gemini)),
                     js=True)
                st.success("\u2705 Chiave ricordata su questo dispositivo: non la "
                           "devi più reinserire. Resta solo tua.")
            st.checkbox(
                "Condividi la chiave con TUTTI gli utenti dell'app",
                key="ricorda_chiave",
                help="Salva la chiave sul server di Streamlit: tutti potranno "
                     "usare Gemini, ma la quota gratuita e' condivisa. "
                     "Consigliato solo se l'app resta per te e i tuoi cari.",
            )
            if st.session_state.get("ricorda_chiave") and _chiave_gemini:
                if ricorda_chiave_gemini(_chiave_gemini):
                    st.success("\u2705 Chiave salvata sul server: da ora in poi "
                               "Gemini e' attivo per tutti.")
                    st.rerun()
    # le chiavi dell'utente salvate nel SUO browser (cookie): hanno la
    # precedenza su quelle del server
    _kb = chiavi_browser() or {}
    if _kb.get("treblo"):
        st.session_state.setdefault("chiave_treblo", _kb["treblo"])
    if _kb.get("hf"):
        st.session_state.setdefault("token_hf", _kb["hf"])
    _chiave_treblo = st.text_input(
        "Chiave Treblo (facoltativa, gratis)",
        value=st.session_state.get("chiave_treblo")
        or _segreto("TREBLO_API_KEY"),
        type="password",
        help="Serve per il motore 'Treblo': e' quello che CANTa il testo "
             "e ti lascia scaricare l'audio (quindi il video e' tutto "
             "automatico). La prendi gratis su treblo.com -> account "
             "sviluppatore (3.000 crediti = 30 canzoni). Resta nel tuo "
             "browser.",
        key="chiave_treblo",
    )
    # (il valore e' gia' in session_state["chiave_treblo"] tramite il key del widget;
    #  non lo riscrivo qui per evitare StreamlitWidgetAlreadyInstantiatedError)
    _token_hf = st.text_input(
        "Token Hugging Face (facoltativo, gratis)",
        value=st.session_state.get("token_hf") or _segreto("HF_TOKEN"),
        type="password",
        help="Serve SOLO per ACE-Step e MusicGen (i modelli open source): "
             "senza token questi spazi pubblici hanno la quota GPU esaurita. "
             "Lo prendi gratis su https://huggingface.co/settings/tokens "
             "(New token -> Read). Resta nel tuo computer.",
        key="token_hf",
    )
    # (il valore e' gia' in session_state["token_hf"] tramite il key del widget)
    _chiave_ia = st.text_input(
        "Chiave API OpenAI (opzionale)",
        value=chiave_da_secrets(),
        type="password",
        help="Lasciala vuota se usi Gemini o l'IA gratuita. Va in "
             ".streamlit/secrets.toml per non riscriverla.",
        key="chiave_ia",
    )
    html(
        "<div class=\"note\">La chiave OpenAI (se la metti) resta nel tuo "
        "browser, come le altre. Con la chiave l'app chiama l'IA solo "
        "quando lo chiedi tu.</div>")

    # ---- IL PANNELLO "ATTIVA TUTTO" ----
    # Un posto solo dove si vede cosa manca, come si prende ogni chiave,
    # e un pulsante che la verifica davvero.
    st.markdown("---")
    with st.expander("\u2699\uFE0F Attiva tutto (2 minuti)",
                     expanded=not bool(chiave_gemini_da_secrets())):
        attiva.pannello(st, html, esc)

    st.markdown("---")

    # ---- stato di TikTok: subito in alto, senza dover fare il flusso ----
    try:
        import tiktok_pubblica as _tkstato
        if _tkstato.collegato():
            html('<div class="note box-ok">\u2705 <b>TikTok pronto</b> per '
                 'l\'auto-pubblicazione: le chiavi ci sono. In fondo, in '
                 '"Pubblica su TikTok", trovi "Collega il tuo TikTok".</div>')
        else:
            html('<div class="note">\U0001F517 <b>TikTok</b>: per '
                 'l\'auto-pubblicazione servono le chiavi della tua '
                 'developer app. Le metti in fondo, in "Pubblica su TikTok" '
                 '&rarr; "Le chiavi della mia developer app".</div>')
    except Exception:
        pass

    # ---- CONFIGURAZIONE (per chi scarica l'app) ----
    # Ogni utente crea le PROPRIE chiavi con la PROPRIA email e l'app
    # gli funziona al 100%: niente altro da fare.
    _stato = stato_configurazione()
    if not (_stato.get("gemini") or _stato.get("suno")):
        with st.expander("\U0001F9E9 Attiva tutto (2 minuti)",
                         expanded=True):
            html(
                '<div class="box"><b>Questa app funziona gia\' cosi\'.</b> '
                'Ma per l\'interpretazione scritta come un maestro della '
                'Scrittura (e per la canzone cantata) servono due chiavi. '
                '<b>Le crei tu, con la tua email</b>, in due minuti: '
                '<ol style="margin:6px 0 0 18px;padding:0">'
                '<li>premi il pulsante sotto: si apre la pagina ufficiale di '
                'Google</li>'
                '<li>crei la chiave (e\' gratis, e la fa per il tuo '
                'account)</li>'
                '<li>la incolli qui e premi "Attiva": <b>subito</b> '
                'l\'app usa la tua chiave</li>'
                '</ol>'
                'Nessun altro vede la tua chiave: resta nel tuo browser.'
                '</div>')

            # --- passo 1+2: Gemini ---
            html('<div class="step">PASSO 1</div>'
                  '<b>Crea la tua chiave Gemini (gratis)</b>')
            if st.link_button("\U0001F310 Apri Google AI Studio "
                              "(crea la chiave qui)",
                              "https://aistudio.google.com/api-keys",
                              use_container_width=True):
                st.info("Si e' aperta una nuova scheda: clicca 'Create API "
                        "key', poi torna qui e incolla la chiave.")
            _v_gem = st.text_input(
                "PASSO 2 - incolla qui la tua chiave Gemini",
                type="password", key="cfg_gemini",
                placeholder="AIzaSy...",
                help="La trovi subito dopo averla creata su "
                     "aistudio.google.com/api-keys.")
            if _v_gem:
                st.session_state["cfg_gemini"] = _v_gem.strip()

            # --- passo 3: attiva ---
            html('<div class="step">PASSO 3</div>'
                  '<b>Attiva e verifica</b>')
            _b1, _b2 = st.columns(2)
            with _b1:
                if st.button("\U0001F4DD Attiva subito (per me)",
                             use_container_width=True, key="cfg_attiva"):
                    if _v_gem:
                        st.session_state["cfg_gemini"] = _v_gem.strip()
                        st.success("\u2705 Attivata! Prova 'Studia questo "
                                   "passaggio': l'interpretazione la scrive "
                                   "Gemini con la TUA chiave.")
                    else:
                        st.info("Incolla prima la chiave (passo 2).")
            with _b2:
                if st.button("\U0001F50E Verifica che funzioni",
                             use_container_width=True, key="cfg_verifica"):
                    _k = _chiave_gemini_attiva()
                    if not _k:
                        st.info("Nessuna chiave attiva: incollane una.")
                    else:
                        with st.spinner("Verifico con una frase sola..."):
                            _r = _chiedi_ia("Rispondi con una sola parola: "
                                             "quale e' il pastore buono?",
                                             chiave_gemini=_k)
                        if _r.get("testo"):
                            st.success("\u2705 Funziona! La chiave e' "
                                       "attiva e risponde.")
                        else:
                            st.error("La chiave non ha risposto: "
                                     + str(_r.get("errore"))[:160])

            st.markdown("---")
            with st.expander("Opzionale: la canzone cantata (Suno)"):
                html('<div class="note">Per sentire una canzone cantata che '
                     'nascendo dal tuo versetto, servono i crediti di un '
                     'motore musicale. Sono opzionali: senza, l\'app cerca '
                     'le canzoni di lode gia\' esistenti e prepara il video.'
                     '</div>')
                if st.button("\U0001F4DD Salva la configurazione sul computer",
                             use_container_width=True, key="cfg_salva"):
                    _da = {}
                    if _v_gem:
                        _da["GEMINI_API_KEY"] = _v_gem.strip()
                    if _da:
                        _okc, _msg = scrivi_secrets(_da)
                        (st.success if _okc else st.error)(
                            "\u2705 " + _msg if _okc else _msg)
                    else:
                        st.info("Incolla prima una chiave.")
                if st.checkbox("Condividi la chiave con TUTTI gli utenti "
                               "dell'app (la quota sara' di tutti)",
                               value=False, key="cfg_condividi"):
                    if _v_gem and ricorda_chiave_gemini(_v_gem.strip()):
                        st.success("\u2705 Chiave salvata sul server: da ora "
                                   "in poi Gemini e' attivo per tutti.")
    # --- Suno: i crediti gratuiti del TUO account (sempre visibile) ---
    with st.expander("Suno: i crediti gratuiti del TUO account"):
        html('<div class="box">'
             + ISTRUZIONE_SUNO.replace("\n", "<br>") + '</div>')
        st.link_button(
            "\U0001F310 Apri suno.com (per copiare il cookie)",
            "https://suno.com/library",
            use_container_width=True)
        _cookie_suno = st.text_input(
            "Incolla qui il cookie di suno.com",
            type="password",
            placeholder="__client=... oppure __session=...",
            help="Lo copi da suno.com (F12 -> Network -> una "
                 "richiesta -> Request Headers -> riga 'cookie'). "
                 "Resta nel TUO browser: non passa da nessun "
                 "altro e non finisce su GitHub.",
            key="campo_cookie_suno",
        )
        _c1, _c2 = st.columns(2)
        with _c1:
            if st.button("\u2705 Attiva subito (per me)",
                         use_container_width=True,
                         key="attiva_cookie_suno"):
                if _cookie_suno:
                    st.session_state["cookie_suno"] = \
                        _cookie_suno.strip()
                    _msg = salva_cookie_suno(_cookie_suno)
                    st.success("\u2705 " + _msg)
                    st.rerun()
                else:
                    st.info("Incolla prima il cookie.")
        with _c2:
            if st.button("\U0001F50E Verifica i crediti",
                         use_container_width=True,
                         key="verifica_crediti_suno"):
                _ok, _nota = suno_disponibile()
                (st.success if _ok else st.error)(
                    "\u2705 " + _nota if _ok else _nota)

    st.markdown("---")
    st.markdown("### \U0001F510 Archivio privato")
    html(
        '<div class="note">L\'archivio e\' privato: quello che cerchi resta '
        'solo per te.<br><br>Per ritrovare i tuoi post anche dopo aver '
        'chiuso il browser, metti un <b>codice</b>: scorri in basso fino a '
        '<b>ARCHIVIO</b>.</div>')


# --------------------------------------------------------------------------
# Intestazione
# --------------------------------------------------------------------------

html(
    """
    <div class="hero">
      <h1>\U0001F3B5 CANTICO</h1>
      <p><b>Dalla Parola alla Lode.</b> Scrivi un versetto o un pensiero:
         l'app trova il testo biblico, lo studia con la dottrina evangelica
         pentecostale, cerca la canzone giusta e ti prepara il post
         per TikTok.</p>
    </div>
    """)

# ==========================================================================
# --------------------------------------------------------------------------
# LA GUIDA: appena aperta, l'app ti dice cosa fare
# --------------------------------------------------------------------------

_ha_gemini = bool(_chiave_gemini_attiva())
_ha_treblo = bool(st.session_state.get("chiave_treblo", "").strip())
# per Suno non facciamo nessuna chiamata (sarebbe lenta): controlliamo
# solo se il cookie c'e'
try:
    import suno as _suno_mod
    _ha_suno = bool(_suno_mod._cookie_grezzo())
except Exception:
    _ha_suno = False

with st.expander("\U0001F9ED Come si usa (4 passaggi) e il tuo stato",
                 expanded=False):
    html(
    f"""
    <div class="box" style="border-left:4px solid #3b6ef5;">
      <h3 style="margin:.1rem 0 .5rem 0;">\U0001F9ED Come si usa (4 passaggi)</h3>
      <ol style="margin:.2rem 0 .4rem 0;padding-left:1.2rem;">
        <li>Scrivi il tuo pensiero o il versetto nella casella qui sotto
            e premi <b>\U0001F50D Trova il testo adatto</b>.</li>
        <li>Scegli il versetto che ti risuona e premi
            <b>\U0001F9E0 Studia questo passaggio</b> (l'interpretazione).</li>
        <li>Premi <b>\U0001F50E Trova Canzone Adatta</b>: 15 inni con la
            spiegazione di perche' sono adatti. Poi <b>Copia Titolo</b> e
            cercalo nella libreria audio di TikTok.</li>
        <li>Premi <b>\U0001F4E4 Salva nell'archivio</b>: il post e' pronto
            (caption, hashtag, data e ora). Poi pubblichi.</li>
      </ol>
      <div class="note" style="margin-top:.4rem;">
        <b>Manca qualcosa?</b> Apri la barra laterale (☰ in alto a
        sinistra) e guarda <b>⚙️ Attiva tutto</b>: l\'app ti dice cosa ti
        serve, ti apre la pagina giusta e <b>verifica la chiave</b> cosi
        sai subito se funziona.
      </div>
      <div class="note" style="margin-top:.4rem;">
        <b>Vuoi anche una canzone NUOVA cantata e il video .mp4?</b>
        Nella sezione <b>\U0001F3B6 Crea una canzone ORIGINALE</b>:
        metti la chiave <b>Treblo</b> (gratis, un minuto) e premi
        <b>\U0001F3AC FAI TUTTO</b>: l'app scrive le parole, fa cantare il
        brano e monta il video verticale, tutto da sola.
      </div>
      <div class="note" style="margin-top:.5rem;">
        <b>Il tuo stato adesso:</b><br>
        &bull; Interpretazione con Gemini: {'\u2705 attiva' if _ha_gemini else '\u274c metti la chiave (barra laterale)'}<br>
        &bull; Canzone cantata + video: {'\u2705 attivo' if _ha_treblo else '\u274c manca la chiave Treblo (gratis)'}<br>
        &bull; I tuoi crediti Suno: {'\u2705 collegati' if _ha_suno else '\u274c non collegati (facoltativo)'}
      </div>
    </div>
    """)

NOTA_TRADUZIONE = (
    '<div class="note">Testo biblico: <b>Sacra Bibbia - Versione Riveduta 2020</b> '
    "(traduzione <b>evangelica protestante</b>, la linea delle chiese "
    "pentecostali/ADI: <b>66 libri</b> = canon protestante, non cattolico. "
    "L'app usa solo questa, mai la traduzione cattolica.</div>"
)


# --------------------------------------------------------------------------

# --------------------------------------------------------------------------
# DUE MODALITA' a schede: per versetto, oppure ricerca in tutta la Bibbia
# --------------------------------------------------------------------------
def _genera_musica(motore: str, testi: str, tag: str, stile: str) -> dict:
    """Genera la musica con il motore scelto. Restituisce un dizionario."""
    # lo stile scritto dall'utente + i tag fissi: arrivano a tutti i motori
    _tag_completo = f"{stile}, {tag}" if stile else tag
    if motore.startswith("Treblo"):
        return genera_canzone_treblo(testi, _tag_completo)
    if motore.startswith("Suno"):
        return genera_canzone_suno(testi, _tag_completo)
    if motore.startswith("Melodia"):
        try:
            import musica as _mus
            return _mus._genera_melodia(testi, timeout=300, stile=_tag_completo)
        except Exception as _exc:
            return {"ok": False, "errore": f"Melodia: {str(_exc)[:120]}",
                    "file": "", "motore": "Melodia"}
    _stile_completo = f"{stile}, {tag}" if stile else tag
    if motore.startswith("ACE-Step"):
        return genera_canzone_gratuita(testi, _stile_completo,
                                       modello="ace-step")
    return genera_canzone_gratuita(testi, _stile_completo, modello="musicgen")


tab_verso, tab_biblia, tab_riflessione = st.tabs([
    "\U0001F3A5 Versetto -> canzone",
    "\U0001F4D6 Cerca in tutta la Bibbia",
    "\U0001F4DD Mia riflessione",
])

with tab_verso:
    # ==========================================================================

    html('<div class="step">PASSAGGIO 1</div><h3>\U0001F4DD Scrivi il tuo testo</h3>')

    # Se c'è una correzione in attesa, il pannello sta PRIMA della text area
    # (così il bottone "Applica" può aggiornare il campo senza errori di stato).
    correzione = st.session_state["correzione"]
    if correzione and correzione.get("problemi"):
        html(
            f'<div class="box box-ok">'
            f'<b>Testo corretto</b><br>{esc(correzione["testo"])}</div>')
        with st.expander(f"Correzioni trovate ({len(correzione['problemi'])})", expanded=True):
            for p in correzione["problemi"]:
                html(
                    f'<div class="note">\u2022 <b>{esc(p.get("breve") or p.get("messaggio", ""))}</b>'
                    f' &mdash; <i>{esc(p.get("evidenzia", ""))}</i>'
                    f'{" \u2192 " + esc(", ".join(p.get("sostituzioni", [])[:3])) if p.get("sostituzioni") else ""}'
                    f'</div>')
        if st.button("\u2705 Applica il testo corretto", use_container_width=True):
            st.session_state["testo_input"] = correzione["testo"]
            st.session_state["correzione"] = None
            st.rerun()
    elif correzione:
        st.info("\u2705 Il tuo testo è già corretto: nessun errore rilevato.")

    testo = st.text_area(
        "Versetto, capitolo o pensiero (es. Marco 12,28-31)",
        placeholder=(
            "Es. «Il Signore è il mio pastore: nulla mi mancherà.»\n"
            "Oppure: «Dio, per il tuo amore io Ti ringrazio»"
        ),
        key="testo_input",
        height=170,
        max_chars=2000,
        label_visibility="collapsed",
    )

    stile_scelto = st.selectbox(
        "Stile della lode cercata",
        list(STILI.keys()),
        index=0,
        help="Sceglie il filtro che viene aggiunto alla tua ricerca. "
             "Consigliato: 'Lodi pentecostali / ADI'.",
        key="stile_lode",
    )

    if testo and len(testo) > 1900:
        html('<div class="note">Testo troncato a 2000 caratteri '
                    '(per non rallentare la ricerca).</div>')

    col1, col2 = st.columns(2)
    with col1:
        if st.button("\u2728 Correggi il testo", use_container_width=True):
            if not (testo or "").strip():
                st.warning("Incolla prima il testo da correggere \U0001F4D8")
            else:
                with st.spinner("Controllo grammaticale..."):
                    st.session_state["correzione"] = correggi_testo(testo)
                    st.session_state["analisi"] = analizza_testo(
                        st.session_state["correzione"]["testo"],
                        estrai_parole_chiave(st.session_state["correzione"]["testo"]),
                    )
                st.rerun()
    with col2:
        if st.button("\U0001F4D6 Trova il testo adatto", use_container_width=True):
            if not (testo or "").strip():
                st.warning("Scrivi prima una parola, una frase o un pensiero \U0001F4D8")
            else:
                with st.spinner("\U0001F50D Cerco il versetto che parla al tuo pensiero..."):
                    try:
                        st.session_state["versetti"] = cerca_versetti_cached(testo.strip(), 5)
                    except Exception as exc:
                        st.error(f"\u26A0\uFE0F Errore nella ricerca del testo biblico: {exc}")
                        st.session_state["versetti"] = []
                if not st.session_state["versetti"]:
                    st.info("Nessun versetto trovato. Prova con parole piu' semplici "
                            "oppure scrivi il versetto per intero.")
                else:
                    _n_v = len(st.session_state["versetti"])
                    _esatto = st.session_state["versetti"][0].get("esatto")
                    st.success(
                        f"\u2705 Ho cercato: {st.session_state['versetti'][0].get('riferimento','')}"
                        + ("" if not _esatto else " (esatto: quello che hai scritto)")
                        + f" \u2014 e altri {_n_v - 1} versetti simili qui sotto."
                        + " Scegli quello che ti parla e premi "
                          "\u201cUsa questo testo\u201d o \u201cTrova la canzone\u201d.")

    # la ricerca delle canzoni vere su YouTube e' stata tolta: l'app dà
    # solo il titolo da cercare su TikTok (la libreria audio di TikTok non
    # e' leggibile dal server). Per il post, la strada principale e' "Crea
    # una canzone ORIGINALE" -> "FAI TUTTO" (parole + canto + poster + video).
    # la mia riflessione: scrivi quello che pensi sulla Parola di Dio
    html(
        '<div class="note" style="margin-top:10px;">'
        '<b>Hai letto la Parola e ti ha parlato?</b> Nella scheda '
        '<b>"\U0001F4DD Mia riflessione"</b> scrivi quello che hai pensato: '
        'l\'app lo cerca in tutta la Bibbia, trova il versetto, la canzone e '
        'prepara il post.</div>')

    # richiesta di ricerca lanciata dalla scelta di un versetto
    if st.session_state.get("_cerca_subito"):
        st.session_state["_cerca_subito"] = False
        esegui_ricerca(st.session_state.get("testo_input", ""))

    # --------------------------------------------------------------------------

with tab_biblia:
    # --------------------------------------------------------------------------

    st.markdown(
        '<hr><div class="step">CERCA LIBERA</div>'
        '<h3>\U0001F4D6 Cerca in tutta la Bibbia</h3>'
        '<div class="note">Scrivi un libro ("genesi", "apocalisse"), un tema '
        '("pastore", "Pentecoste", "misericordia") o una parola: esce il '
        'passaggio completo, e sotto scegli cosa approfondire.</div>'
        + NOTA_TRADUZIONE +
        '</div>',
        unsafe_allow_html=True,
    )

    _col_a, _col_b = st.columns([3, 1])
    with _col_a:
        _query = st.text_input(
            "Cerca un libro, un tema o una parola",
            value=st.session_state.get("query_biblia", ""),
            placeholder="es. genesi, apocalisse, pastore, Pentecoste, consolazione",
            key="query_biblia",
            label_visibility="collapsed",
        )
    with _col_b:
        if st.button("\U0001F50E Cerca", key="btn_cerca_biblia", use_container_width=True):
            if not (_query or "").strip():
                st.warning("Scrivi prima cosa vuoi cercare \U0001F4DD")
            else:
                with st.spinner("\U0001F50D Cerco in tutta la Bibbia..."):
                    _libri = cerca_libri(_query)
                    _passaggi = [] if _libri else cerca_passaggi(_query, contesto=2,
                                                               max_passaggi=10)
                st.session_state["biblia_libri"] = _libri
                st.session_state["biblia_passaggi"] = _passaggi
                st.session_state["biblia_query"] = _query
                st.rerun()

    _libri = st.session_state.get("biblia_libri") or []
    _passaggi = st.session_state.get("biblia_passaggi") or []

    if _libri:
        st.markdown(
            f'<div class="box box-ok"><b>\U0001F4D6 Libri trovati per '
            f'"{esc(st.session_state.get("biblia_query", ""))}"</b></div>',
            unsafe_allow_html=True,
        )
        for _libro in _libri[:4]:
            _capitoli = capitoli_del(_libro)
            with st.container(border=True):
                st.markdown(
                    f'<div class="card-title">\U0001F4D6 {esc(_libro)}</div>'
                    f'<div class="card-meta">{len(_capitoli)} capitoli</div>',
                    unsafe_allow_html=True,
                )
                _cap = st.selectbox("Capitolo", _capitoli, index=0,
                                    key=f"cap_{_libro}", label_visibility="collapsed")
                _testo_cap = testo_capitolo(_libro, _cap)
                with st.expander(f"Leggi {_libro} {_cap} (testo completo)", expanded=True):
                    st.markdown(
                        f'<div class="box" style="max-height:460px;overflow:auto;'
                        f'white-space:pre-wrap;">{esc(_testo_cap)}</div>',
                        unsafe_allow_html=True,
                    )
                _c1, _c2 = st.columns(2)
                with _c1:
                    blocco_copia(_testo_cap, f"copia_{_libro}_{_cap}",
                                 "\U0001F4CB Copia il capitolo")
                with _c2:
                    if st.button("\U0001F50E Studia questo capitolo",
                                 key=f"studia_{_libro}_{_cap}", use_container_width=True):
                        st.session_state["riferimento_forzato"] = {
                            "libro": _libro, "libro_en": "", "abbreviazione": "",
                            "capitolo": _cap, "versetto": 1, "versetto_fine": None,
                            "riferimento": f"{_libro} {_cap}",
                            "riferimento_en": f"{_libro} {_cap}",
                        }
                        st.rerun()

    elif _passaggi:
        st.markdown(
            f'<div class="box box-ok"><b>\U0001F4D6 Passaggi trovati per '
            f'"{esc(st.session_state.get("biblia_query", ""))}"</b>'
            '<br><span class="note">Ecco il testo completo del paragrafo. '
            'Sotto scegli cosa vuoi approfondire.</span></div>',
            unsafe_allow_html=True,
        )
        for _i, _p in enumerate(_passaggi, start=1):
            with st.container(border=True):
                st.markdown(
                    f'<div class="badge">#{_i}</div>'
                    f'<div class="card-title">\U0001F4D6 {esc(_p["riferimento"])}</div>'
                    f'<div class="card-meta">{_p["n_versetti"]} versetti '
                    f'&bull; trovato in: {esc(", ".join(_p["corrispondenze"][:5]))}</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<div class="box" style="max-height:380px;overflow:auto;'
                    f'white-space:pre-wrap;">{esc(_p["testo"])}</div>',
                    unsafe_allow_html=True,
                )
                _c1, _c2 = st.columns(2)
                with _c1:
                    blocco_copia(_p["testo"], f"copia_pass_{_i}", "\U0001F4CB Copia")
                with _c2:
                    if st.button("\U0001F50E Studia questo passaggio",
                                 key=f"studia_pass_{_i}", use_container_width=True):
                        st.session_state["riferimento_forzato"] = {
                            "libro": _p["libro"], "libro_en": "",
                            "abbreviazione": "", "capitolo": _p["capitolo"],
                            "versetto": 1, "versetto_fine": None,
                            "riferimento": _p["riferimento"],
                            "riferimento_en": _p["riferimento"],
                        }
                        st.rerun()

        st.markdown(
            '<div class="step">APPROFONDISCI</div>'
            '<h3>\U0001F50E Cosa vuoi approfondire?</h3>',
            unsafe_allow_html=True,
        )
        _opzioni = [p["riferimento"] for p in _passaggi]
        _scelta = st.selectbox("Scegli il passaggio da studiare", _opzioni, index=0,
                               key="approfondisci_passaggio")
        _numeri = st.text_input(
            "Quali numeri vuoi vedere? (opzionale)",
            value="",
            placeholder="es. 12,28-31  oppure  23  oppure  1-6",
            key="approfondisci_numeri",
            help="Lascia vuoto per studiare tutto il passaggio. Scrivi i numeri "
                 "per restringere (capitolo, capitolo-versetto, o intervallo).",
        )
        if st.button("\U0001F50D Applica e studia", key="btn_approfondisci",
                     type="primary", use_container_width=True):
            _p = _passaggi[_opzioni.index(_scelta)]
            _rif = {"libro": _p["libro"], "libro_en": "", "abbreviazione": "",
                    "capitolo": _p["capitolo"], "versetto": 1, "versetto_fine": None,
                    "riferimento": _scelta, "riferimento_en": _scelta}
            if _numeri.strip():
                _r2 = rileva_riferimento(f'{_p["libro"]} {_p["capitolo"]} {_numeri}')
                if _r2 and _r2.get("versetto"):
                    _rif = _r2
            st.session_state["riferimento_forzato"] = _rif
            st.rerun()

    else:
        st.markdown(
            '<div class="note">Nessuna ricerca fatta ancora. Prova con un esempio: '
            '"pastore", "Pentecoste", "genesi", "consolazione".</div>',
            unsafe_allow_html=True,
        )

    # ==========================================================================

with tab_riflessione:
    # ==========================================================================
    # MIA RIFLESSIONE: scrivi quello che pensi sulla Parola di Dio,
    # l'app trova il versetto, la canzone e prepara il post.
    # ==========================================================================

    html(
        '<div class="step">LA MIA RIFLESSIONE</div>'
        "<h3>\U0001F4DD Scrivi quello che pensi sulla Parola di Dio</h3>"
        '<div class="note">Ogni giorno, quando leggi la Bibbia, annota quello '
        'che ti ha toccato il cuore. Scrivilo qui: l\'app <b>lo cerca in tutta '
        'la Bibbia</b>, trova il versetto che parla proprio a te, lo studia, '
        'cerca la canzone giusta e ti prepara il post da pubblicare.</div>'
        + NOTA_TRADUZIONE +
        '</div>')

    _riflessione = st.text_area(
        "La mia riflessione (scrivi con parole tue)",
        placeholder=(
            "Es. «Dio non abbandona nessuno: anche quando mi sento solo, "
            "lui c'è.»\n"
            "Es. «Oggi ho capito che la pazienza non è aspettare: è "
            "continuare a fidarsi.»\n"
            "Es. «Il perdono libera prima chi lo chiede.»"
        ),
        key="testo_riflessione",
        height=190,
        max_chars=2000,
    )

    st.checkbox(
        "Fai scegliere il versetto all'IA (il piu' adatto alla mia riflessione)",
        value=st.session_state.get("usa_ia_versetto", True),
        key="usa_ia_versetto",
        help="L'IA guarda i 5 versetti trovati per parole simili e sceglie "
             " quello che parla davvero al tuo cuore. Ci mette 10-30 secondi. "
             "Senza IA l'app usa solo il confronto delle parole.",
    )

    _col_r1, _col_r2 = st.columns(2)
    with _col_r1:
        if st.button("\U0001F50D Trova il versetto migliore per la mia "
                     "riflessione",
                     type="primary", use_container_width=True,
                     key="cerca_riflessione"):
            if not (_riflessione or "").strip():
                st.warning("Scrivi prima la tua riflessione \U0001F4DD")
            else:
                with st.spinner("\U0001F50D Cerco in tutta la Bibbia il "
                                "versetto che parla alla tua riflessione..."):
                    try:
                        st.session_state["versetti"] = cerca_versetti_cached(
                            _riflessione.strip(), 5)
                        st.session_state["versetti_da_riflessione"] = True
                        st.session_state["riflessione_giornaliera"] = \
                            _riflessione.strip()
                        st.session_state["scelta_ia_versetto"] = None
                    except Exception as exc:
                        st.error(f"\u26A0\uFE0F Errore nella ricerca: {exc}")
                        st.session_state["versetti"] = []
                # l'AI sceglie il versetto che parla davvero alla riflessione
                if st.session_state.get("versetti") and st.session_state.get(
                        "usa_ia_versetto", True):
                    with st.spinner("\U0001F9E0 Chiedo all'IA quale versetto "
                                    "parla davvero alla tua riflessione..."):
                        _sc = scegli_versetto_ia(
                            _riflessione.strip(),
                            st.session_state["versetti"],
                            chiave_gemini=_chiave_gemini_attiva(),
                            chiave_openai=st.session_state.get("chiave_ia", ""))
                    st.session_state["scelta_ia_versetto"] = _sc
                    if _sc.get("indice") is not None:
                        # il versetto scelto dall'IA va per primo
                        _v = st.session_state["versetti"].pop(_sc["indice"])
                        st.session_state["versetti"].insert(0, _v)
                    elif _sc.get("riferimento"):
                        # l'IA ha proposto un versetto migliore: lo cerco
                        # nella Bibbia e lo metto per primo
                        _rif_ia = _sc["riferimento"]
                        try:
                            _r2 = rileva_riferimento(_rif_ia)
                            if _r2 and _r2.get("versetto"):
                                _sv = trova_versetto(
                                    _r2["libro"], _r2["capitolo"],
                                    _r2["versetto"],
                                    contesto=0,
                                    versetto_fine=_r2.get("versetto_fine"))
                                if _sv:
                                    _sv["temi"] = []
                                    st.session_state["versetti"].insert(0, _sv)
                        except Exception:
                            pass
                if not st.session_state["versetti"]:
                    st.info("Nessun versetto trovato. Prova con parole "
                            "piu' semplici, oppure scrivi un tema "
                            "(es. 'fede', 'consolazione', 'pastore').")
    with _col_r2:
        if st.button("\U0001F3B5 Genera la canzone dalla mia riflessione",
                     type="primary", use_container_width=True,
                     key="canzone_da_riflessione"):
            if not (_riflessione or "").strip():
                st.warning("Scrivi prima la tua riflessione \U0001F4DD")
            else:
                _rif = _riflessione.strip()
                with st.spinner("\U0001F3B5 L'IA cerca il versetto che parla "
                                "alla tua riflessione e scrive le parole del "
                                "brano..."):
                    _rif_versetto = ""
                    _rif_testo = ""
                    try:
                        _vers = cerca_versetti_cached(_rif, 3)
                        if _vers:
                            _sc = scegli_versetto_ia(
                                _rif, _vers,
                                chiave_gemini=_chiave_gemini_attiva(),
                                chiave_openai=st.session_state.get("chiave_ia",
                                                                     ""))
                            if _sc.get("indice") is not None:
                                _v = _vers[min(int(_sc["indice"]),
                                               len(_vers) - 1)]
                                _rif_versetto = str(_v.get("riferimento", "")
                                                    or _v.get("riferimento_testo",
                                                              ""))
                                _rif_testo = str(_v.get("testo", "") or "")
                            elif _sc.get("riferimento"):
                                _rif_versetto = str(_sc["riferimento"])
                    except Exception:
                        pass
                    try:
                        from testi_canzone import scrivi_testi_da_riflessione
                    except Exception:
                        scrivi_testi_da_riflessione = None
                    if scrivi_testi_da_riflessione is None:
                        _res = {"ok": False, "errore": (
                            "Questa versione non ha ancora la scrittura "
                            "dalla riflessione: aggiorna l'app (Ricarica la "
                            "versione piu' recente) e riprova.")}
                    else:
                        _res = scrivi_testi_da_riflessione(
                            _rif, riferimento=_rif_versetto,
                            testo_versetto=_rif_testo,
                            temi=", ".join(estrai_parole_chiave(_rif, 3)),
                            chiave_gemini=_chiave_gemini_attiva(),
                            chiave_openai=st.session_state.get("chiave_ia", ""))
                if _res.get("ok"):
                    st.session_state["canzone_testi"] = _res["testo"]
                    st.session_state["riflessione_giornaliera"] = _rif
                    st.session_state["canzone_dalla_riflessione"] = True
                    st.success("\u2705 Ecco il brano nato dalle tue parole! "
                               "Scorri in basso, in \u201cCrea una canzone "
                               "ORIGINALE\u201d: le parole sono gia' pronte, "
                               "scegli il motore e premi \u201cComponi e "
                               "canta\u201d.")
                else:
                    st.warning(_res.get("errore", ""))
        if st.button("\U0001F4D6 Pubblica la riflessione di oggi",
                     use_container_width=True, key="pubblica_riflessione"):
            if not (_riflessione or "").strip():
                st.warning("Scrivi prima la tua riflessione \U0001F4DD")
            else:
                # salva la riflessione e preparala per il post
                st.session_state["riflessione_giornaliera"] = _riflessione.strip()
                _data_oggi = date.today().strftime("%d/%m/%Y")
                _kw_rif = ", ".join(estrai_parole_chiave(_riflessione, 3))
                st.session_state["post"] = {
                    "titolo": "", "video_id": "", "canale": "",
                    "hashtag": [], "formato": "Versetto + domanda",
                    "caption": (f"«{_riflessione.strip()}»\n\n"
                                f"Parole chiave: {_kw_rif}\n"
                                f"\U0001F4DD Riflessione del {_data_oggi}"),
                    "hook": " ".join(_riflessione.strip().split()[:8]),
                }
                st.success("\u2705 Riflessione salvata. Ora scrivi il versetto "
                           "nella scheda \"Versetto -> canzone\" e l'app "
                           "cercherà la canzone per la tua Parola.")

        # ---- LA TUA RIFLESSIONE RIDOTTA PER TIKTOK ----
        if st.button("\U0001F50D Riduci la mia riflessione in un post TikTok",
                     use_container_width=True, key="riduci_riflessione_utente"):
            if not (_riflessione or "").strip():
                st.warning("Scrivi prima la tua riflessione \U0001F4D8")
            else:
                with st.spinner("\U0001F50D Riduco la tua riflessione per "
                                "TikTok..."):
                    _post_mio = riduci_per_post(
                        _riflessione.strip(),
                        chiave_gemini=_chiave_gemini_attiva(),
                        chiave_openai=st.session_state.get("chiave_ia", ""))
                _salva_riflessione_ia(_riflessione.strip(), _post_mio,
                                      fonte="la tua riflessione")
                st.rerun()

        # il post ricavato dalla TUA riflessione (se l'hai ridotta)
        _post_mio_gia = (st.session_state.get("riflessione_ia") or {}).get(
            "post") or {}
        if _post_mio_gia.get("hook") or _post_mio_gia.get("caption"):
            html('<hr><div class="step">IL TUO POST TIKTOK</div>')
            _mostra_post_ia(_post_mio_gia, "rif")
            if st.button("\U0001F4E4 Usa questo post per il mio TikTok",
                         type="primary", use_container_width=True,
                         key="usa_post_riflessione"):
                _post_gia = st.session_state.get("post")
                if not _post_gia:
                    # niente canzone scelta: il post si fa da solo, con le
                    # parole della riflessione (non serve scegliere una
                    # canzone su YouTube)
                    _hashtag = genera_hashtag(testo,
                                              estrai_parole_chiave(testo, 3))
                    _post_gia = {
                        "titolo": "il tuo versetto", "video_id": "",
                        "canale": "", "hashtag": _hashtag,
                        "formato": "Versetto + domanda",
                        "caption": "", "hook": "",
                    }
                _post_gia = dict(_post_gia)
                _post_gia["caption"] = _post_ia.get("caption", "")
                _post_gia["hook"] = _post_ia.get("hook", "")
                _post_gia["riflessione"] = _rif_ia.get("riflessione", "")
                _post_gia["corpo_ia"] = _post_ia.get("corpo", [])
                _post_gia["cta_ia"] = _post_ia.get("cta", "")
                _post_gia["momento_ia"] = _post_ia.get("momento", {})
                st.session_state["post"] = _post_gia
                # i campi del PASSAGGIO 3 prendono subito il testo dell'IA
                if _post_ia.get("caption"):
                    st.session_state["caption"] = _post_ia["caption"]
                if _post_ia.get("hook"):
                    st.session_state["hook"] = _post_ia.get("hook", "")
                st.success("\u2705 Fatto: nel PASSAGGIO 3 trovi la caption e "
                           "il testo a schermo scritti dall'IA.")