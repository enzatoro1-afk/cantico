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
                _post_gia = st.session_state.get("post")
                if not _post_gia:
                    # niente canzone scelta: il post si fa da solo, con le
                    # parole della riflessione (non serve scegliere una
                    # canzone su YouTube)
                    _hashtag = genera_hashtag(_riflessione,
                                              estrai_parole_chiave(_riflessione, 3))
                    _post_gia = {
                        "titolo": "il tuo versetto", "video_id": "",
                        "canale": "", "hashtag": _hashtag,
                        "formato": "Versetto + domanda",
                        "caption": "", "hook": "",
                    }
                _post_gia = dict(_post_gia)
                _post_gia["caption"] = _post_mio_gia.get("caption", "")
                _post_gia["hook"] = _post_mio_gia.get("hook", "")
                _post_gia["corpo_ia"] = _post_mio_gia.get("corpo", [])
                _post_gia["riflessione"] = _riflessione.strip()
                st.session_state["post"] = _post_gia
                if _post_mio_gia.get("caption"):
                    st.session_state["caption"] = _post_mio_gia["caption"]
                if _post_mio_gia.get("hook"):
                    st.session_state["hook"] = _post_mio_gia["hook"]
                st.success("\u2705 Fatto: nel PASSAGGIO 3 trovi la caption e "
                           "il testo a schermo.")

    # i versetti trovati dalla riflessione vengono mostrati sotto
    # (riutilizzo lo stesso blocco della scheda 1)

    # ==========================================================================

# Analisi del testo (temi, tono, Salmo)
# --------------------------------------------------------------------------

analisi = st.session_state["analisi"]
if analisi:
    temi = "".join(f'<span class="chip">{esc(t)}</span>' for t in analisi["temi"]) or \
           '<span class="chip">generico</span>'
    salmo = analisi.get("salmo")
    riga_salmo = ""
    if salmo:
        riga_salmo = (
            f'<br><b>\U0001F4D6 Salmo rilevato:</b> {esc(salmo["riferimento"])}'
            f' &mdash; {esc(salmo["titolo"])}'
        )
    riga_mood = ""
    try:
        from text_tools import rileva_mood
        _mood = rileva_mood(testo or "")
        if _mood:
            riga_mood = (f'<br><b>Atmosfera:</b> {esc(_mood["etichetta"])} '
                         f'(musica: {esc(", ".join(_mood["parole"]))})')
    except Exception:
        pass

    html(
        f'<div class="box"><b>\U0001F9EA Analisi del testo</b><br>'
        f'<b>Temi:</b> {temi}<br>'
        f'<b>Tono:</b> {esc(analisi["tono"])}<br>'
        f'<b>Durata video consigliata:</b> {esc(analisi["durata_video"])}'
        f'{riga_mood}{riga_salmo}</div>')

    # (gli inni sul Salmo non vengono piu' cercati su YouTube: l'app
    #  prepara la canzone originale da sola)

# --------------------------------------------------------------------------
# IL VERSETTO ESATTO indicato dall'utente (Fase 1 -> Fase 2)
# --------------------------------------------------------------------------

riferimento_verso = (st.session_state.get("riferimento_forzato")
                      or rileva_riferimento(testo or ""))
studio = st.session_state.get("versetto_studio") or {}

if riferimento_verso and not studio.get("errore"):
    # Se l'utente ha scritto un versetto esatto (es. "Salmo 23,1"), quello
    # vince: l'app non deve mostrargli il versetto scelto dall'IA.
    _v_scritto = riferimento_verso.get("versetto")
    if _v_scritto:
        versetto_esatto = trova_versetto(
            riferimento_verso["libro"], riferimento_verso["capitolo"],
            _v_scritto,
            versetto_fine=riferimento_verso.get("versetto_fine"))
    else:
        versetto_esatto = studio.get("versetto") or trova_versetto(
            riferimento_verso["libro"], riferimento_verso["capitolo"], 1,
            versetto_fine=riferimento_verso.get("versetto_fine"))

    solo_capitolo = not riferimento_verso.get("versetto")

    # CONTESTO opzionale: di default vedi SOLO quello che hai chiesto
    mostra_contesto = st.checkbox(
        "Mostra anche i versetti vicini (contesto)",
        value=False,
        help="Spunta per vedere i 2 versetti prima e dopo quello che hai indicato.",
        key="mostra_contesto",
    )
    # INTESTAZIONI POETICHE (es. "Salmo di Davide"): nascoste di default
    mostra_intestazioni = st.checkbox(
        "Mostra anche le intestazioni poetiche (es. 'Salmo di Davide')",
        value=False,
        help="Nella Riveduta alcuni Salmi hanno un titolo poetico prima del "
             "versetto: di default lo nascondo, cosi' vedi solo il testo.",
        key="mostra_intestazioni",
    )

    def _testo_versetto(testo: str) -> str:
        """Solo il testo del versetto, senza intestazioni poetiche."""
        if mostra_intestazioni:
            return testo
        return testo_versetto_pulito(testo)

    if versetto_esatto:
        if solo_capitolo:
            html(
                '<div class="step">IL SALMO/CAPITOLO INTERO</div>'
                f'<h3>\U0001F4D6 {esc(riferimento_verso["libro"])} '
                f'{esc(str(riferimento_verso["capitolo"]))}</h3>'
                f'<div class="note">Testo integrale dalla {esc(NOME_TRADUZIONE)} '
                '(66 libri = canon protestante evangelico).</div>')
            _cap = versetto_esatto.get("capitolo_versetti", [])
            # vuoi solo una parte del capitolo? (es. "prendi dal 18 al 31")
            _intervallo = st.text_input(
                "Vuoi solo alcuni versetti di questo capitolo?",
                value="",
                placeholder="es. 18-31  (oppure: dal 18 al 31)",
                key="intervallo_capitolo",
            )
            if st.button("Applica l'intervallo", key="applica_intervallo",
                         use_container_width=True):
                _rif = rileva_riferimento(
                    f"{riferimento_verso['libro']} {riferimento_verso['capitolo']} "
                    f"{_intervallo}")
                if _rif and _rif.get("versetto"):
                    st.session_state["riferimento_forzato"] = _rif
                    st.rerun()
                else:
                    st.warning("Scrivi l'intervallo, es. 18-31")
            html(
                f'<div class="note">{len(_cap)} versetti: questo e\' tutto il '
                'capitolo. Per un passaggio preciso scrivi es. '
                '"Marco 12,28-31".</div>')
            for c in _cap:
                html(
                    f'<div class="box" style="margin-bottom:6px;">'
                    f'<b>{esc(c["riferimento"])}</b><br>{esc(c["testo"])}</div>')
        elif versetto_esatto.get("e_passaggio"):
            html(
                '<div class="step">IL PASSAGGIO</div>'
                f'<h3>\U0001F4D6 {esc(versetto_esatto["riferimento"])}</h3>'
                f'<div class="note">Testo integrale dalla {esc(NOME_TRADUZIONE)} '
                '(66 libri = canon protestante evangelico).</div>')
            for c in versetto_esatto.get("passaggio", []):
                html(
                    f'<div class="box" style="margin-bottom:6px;">'
                    f'<b>{esc(c["riferimento"])}</b><br>'
                    f'{esc(_testo_versetto(c["testo"]))}</div>')
            # vuoi studiare solo QUALSI versetto del passaggio?
            # (puo' essere uno solo o un intervallo: "18-21")
            _n = len(versetto_esatto.get("passaggio", []))
            if _n > 1:
                st.text_input(
                    "Studiare in profondita' solo questi versetti?",
                    value="",
                    placeholder="es. 18-21   (lascia vuoto = tutto il passaggio)",
                    key="sotto_passaggio",
                    help="Puoi scrivere un versetto solo (18) o un intervallo "
                         "(18-21). Se lasci vuoto, studia tutto il passaggio.",
                )
        else:
            html(
                '<div class="step">IL VERSETTO ESATTO</div>'
                f'<h3>\U0001F4D6 {esc(versetto_esatto["riferimento"])}</h3>'
                f'<div class="note">Testo integrale dalla {esc(NOME_TRADUZIONE)}: '
                'traduzione <b>evangelica protestante</b> (la linea delle '
                'chiese pentecostali/ADI), <b>66 libri</b> = canon protestante. '
                'Niente traduzione cattolica, niente libri deuterocanonici.'
                '</div>')
            html(
                '<div class="box box-ok"><b>\u2705 OK: questo e\' il '
                'versetto che hai scelto</b><br>'
                '<span class="note">Qui sotto puoi premere '
                '<b>\U0001F50E Studia questo passaggio</b> (l\'interpret '
                'azione), <b>\U0001F50E Trova Canzone Adatta</b> (le canzoni) '
                'o preparare direttamente il post.</span></div>')
            html(
                f'<div class="box"><b>\U0001F4D6 {esc(versetto_esatto["riferimento"])}</b>'
                f'<br><span style="font-size:1.02rem;">{esc(versetto_esatto["testo_pulito"])}</span></div>')

            # ---- COSA VUOI VEDERE? solo il versetto, il capitolo, un intervallo ----
            _v = riferimento_verso.get("versetto")
            _cap_n = riferimento_verso.get("capitolo")
            _ambito = st.radio(
                "Cosa vuoi vedere di questo passaggio?",
                [f"Solo il versetto (v.{_v})" if _v else "Il versetto",
                 f"Tutto il capitolo ({riferimento_verso['libro']} {_cap_n})",
                 "Un intervallo scelto da me"],
                index=0,
                key="ambito_versetto",
                help="Scegli se vedere solo il versetto, tutto il capitolo, "
                     "o un intervallo preciso (es. 14,6-14,10).",
            )
            if _ambito.startswith("Un intervallo"):
                _txt = st.text_input(
                    "Scrivi l'intervallo",
                    value="",
                    placeholder="es. 6-10   oppure  14,6-14,10",
                    key="intervallo_personalizzato",
                )
                if st.button("\U0001F50D Applica l'intervallo",
                             key="applica_intervallo_pers", use_container_width=True):
                    _txt_ok = (_txt or "").strip()
                    if "," in _txt_ok:
                        # l'utente ha scritto il riferimento completo
                        # (es. "8,7"): NON aggiungere il capitolo davanti
                        _rif = rileva_riferimento(
                            f"{riferimento_verso['libro']} {_txt_ok}")
                    else:
                        # solo il versetto o l'intervallo (es. "7", "6-10")
                        _rif = rileva_riferimento(
                            f"{riferimento_verso['libro']} {_cap_n} {_txt_ok}")
                    if _rif and _rif.get("versetto"):
                        st.session_state["riferimento_forzato"] = _rif
                        st.rerun()
                    else:
                        st.warning("Scrivi l'intervallo, es. 6-10 (oppure "
                                   "il versetto esatto, es. 8,7)")
            else:
                _rif = dict(riferimento_verso)
                if _ambito.startswith("Tutto il capitolo"):
                    _rif["versetto"] = 1
                    _rif["versetto_fine"] = None
                    _rif["riferimento"] = (f"{riferimento_verso['libro']} {_cap_n}")
                if st.button("\U0001F50D Applica", key="applica_ambito",
                             use_container_width=True):
                    st.session_state["riferimento_forzato"] = _rif
                    st.rerun()

        contesto = [] if (solo_capitolo or not mostra_contesto) else (
            versetto_esatto.get("contesto_prima", []) +
            versetto_esatto.get("contesto_dopo", []))
        if contesto:
            righe = "".join(
                f'<br><span class="note"><b>{esc(c["riferimento"])}</b> '
                f'{esc(_testo_versetto(c["testo"]))}</span>' for c in contesto)
            html(
                f'<div class="box box-warn"><b>Contesto (versetti vicini)</b>{righe}</div>')

        # testo completo da copiare (passaggio / capitolo / versetto)
        if versetto_esatto.get("e_passaggio"):
            testo_da_copiare = "\n\n".join(
                f'{c["riferimento"]}  {_testo_versetto(c["testo"])}'
                for c in versetto_esatto.get("passaggio", []))
        elif solo_capitolo:
            testo_da_copiare = "\n\n".join(
                f'{c["riferimento"]}  {_testo_versetto(c["testo"])}'
                for c in versetto_esatto.get("capitolo_versetti", []))
        else:
            testo_da_copiare = (f'{versetto_esatto["riferimento"]}  '
                                f'{versetto_esatto["testo_pulito"]}')

        col_c, col_d = st.columns(2)
        with col_c:
            blocco_copia(testo_da_copiare, "copia_testo_verso",
                         "\U0001F4CB Copia il testo")
        with col_d:
            st.link_button(
                "\U0001F4AC Apri ChatGPT",
                "https://chatgpt.com/",
                use_container_width=True,
                help="Incolla il testo copiato e chiedi un Approfondimento",
            )

        col_a, col_b = st.columns(2)
        with col_a:
            _etichetta = "\U0001F50E Studia questo passaggio"
            _sotto = (st.session_state.get("sotto_passaggio") or "").strip()
            if _sotto:
                _etichetta = f"\U0001F50E Studia solo {_sotto}"
            st.button(
                _etichetta,
                key="studia_versetto",
                use_container_width=True,
                on_click=_studia_versetto,
            )
            st.checkbox(
                "Studia con l'IA (Gemini: veloce e profondo)",
                value=st.session_state.get("usa_ia_gratuita", True),
                key="usa_ia_gratuita",
                help="Attivo: l'IA scrive l'interpretazione ed e' diversa per "
                     "ogni versetto. Con la chiave Google Gemini (quella "
                     "gratis di aistudio.google.com/apikey) ci mette pochi "
                     "secondi. Senza chiave prova ChatGPT e, in ultima "
                     "istanza, la IA gratuita: li' puo' capitare di "
                     "aspettare qualche decina di secondi. Spuntalo solo se "
                     "non vuoi che l'IA scriva e preferisci il solo studio "
                     "del versetto (istantaneo).",
            )
            st.checkbox(
                "Fai anche la riflessione e il post TikTok (in automatico)",
                value=st.session_state.get("auto_riflessione", True),
                key="auto_riflessione",
                help="Attivo: dopo l'interpretazione l'IA scrive anche una "
                     "riflessione personale sul versetto e la riduce in un "
                     "post pronto per TikTok (testo a schermo, 3 righe, "
                     "caption, momento giusto). Con Gemini ci mette pochi "
                     "secondi; senza chiave, qualche decina di secondi.",
            )
        with col_b:
            st.button(
                "\U0001F3B5 Canzone per questo versetto",
                key="canzone_da_versetto",
                use_container_width=True,
                on_click=_imposta_testo,
                args=(testo_da_copiare,),
            )

# --- esito dello studio: interpretazione + parole chiave + spiegazioni ---
if studio and studio.get("errore"):
    st.warning(studio["errore"])
elif studio and studio.get("versetto"):
    v = studio["versetto"]
    interp = studio["interpretazione"]

    html(
        '<div class="step">FASE 1 - INTERPRETAZIONE</div>'
        "<h3>\U0001F4D3 L'interpretazione del versetto</h3>")
    if st.session_state.get("ia_note"):
        st.info("Nota: " + st.session_state["ia_note"])
    lunghezza = st.radio(
        "Quanto vuoi leggere dell'interpretazione?",
        ["Completa (tutto il testo)", "Media (abbroncata)", "Breve (riassunto)"],
        index=0,
        horizontal=True,
        key="lunghezza_interp",
        help="Di default esce TUTTO il testo dell'interpretazione.",
    )
    testo_interp = interp.get("testo", "")
    if lunghezza.startswith("Breve"):
        testo_interp = testo_interp[:700]
    elif lunghezza == "Media":
        testo_interp = testo_interp[:2200]
    # "Completa" -> testo integro, senza tagli
    totale = len(interp.get("testo", ""))
    _fonte_int = st.session_state.get("interp_pertinente", "")
    if _fonte_int:
        html(
            f'<div class="note">Interpretazione presa da: <b>{esc(_fonte_int)}</b></div>',
        )
    html(
        '<div class="box"><b>{esc(interp.get("fonte", ""))}</b>'
        f' <span class="note">({totale:,} caratteri totali)</span><br>'
        f'{_md(testo_interp)}</div>')

    # ---- AVVISO: stai usando la IA GRATUITA (lenta)? ----
    _fonte = (interp.get("fonte", "") or "").lower()
    if "gratuita" in _fonte and not _chiave_gemini_attiva():
        html(
            '<div class="box box-warn"><b>\u26A0\uFE0F Stai usando la IA '
            'gratuita</b> (veloce? no: puo\' aspettare qualche decina di '
            'secondi). Con la chiave <b>Google Gemini</b> (gratis) tutto va '
            'molto piu\' veloce e la scrittura e\' piu\' profonda.<br>'
            'Prendila in 1 minuto su '
            '<a href="https://aistudio.google.com/apikey" target="_blank">'
            'aistudio.google.com/apikey</a> e incollala nella barra laterale, '
            'poi premi <b>"Attiva subito (per me)"</b>.</div>')

    # COPIA l'interpretazione (sempre) + SCARICALA
    _nome_file = (f"interpretazione_{v.get('riferimento', 'versetto')}"
                  .replace(" ", "_").replace(",", "-").replace(":", "-"))
    col_i1, col_i2, col_i3 = st.columns(3)
    with col_i1:
        blocco_copia(interp.get("testo", ""), "copia_interp",
                     "\U0001F4CB Copia l'interpretazione")
    with col_i2:
        st.download_button(
            "\U0001F4E4 Scarica (.txt)",
            data=interp.get("testo", ""),
            file_name=f"{_nome_file}.txt",
            mime="text/plain",
            key="dl_interp",
        )
    with col_i3:
        if st.button("\U0001F504 Riscrivi (un'altra versione)",
                     key="riscrivi_interp", use_container_width=True,
                     help="Chiede all'IA un'altra interpretazione dello stesso "
                          "versetto: utile se vuoi un tono diverso o se la "
                          "prima non ti convince."):
            st.session_state["_ia_richiesta"] = "gratis"
            st.rerun()
    parole = _parole_chiave_pulite(interp.get("parole_chiave", []))
    if parole:
        html(
            '<div class="note" style="margin-top:6px;">'
            '<b>Le parole chiave spirituali (usate nella ricerca musicale):</b>'
            '</div><div class="chips">'
            + "".join(f'<span class="chip">{esc(p)}</span>' for p in parole)
            + '</div>')

    # se l'utente ha incollato una nuova interpretazione, ricalcolo le canzoni
    if st.session_state.get("_ria_fase2"):
        st.session_state["_ria_fase2"] = False
        _rif = studio.get("riferimento", {})
        _kw = parole or ["fede", "lode", "consolazione"]
        _rif_breve = _riferimento_breve(_rif) if _rif else ""
        _q = (f"{_rif_breve} {' '.join(_kw)} {FILTRO_PENTECOSTALE} "
              f"{KEYWORD_NEGATIVE}")
        with st.spinner("Rifaccio la ricerca della canzone con le nuove parole chiave..."):
            try:
                _ris = ricerca_cached((_q,), 5, tuple(_kw), DURATA_MAX_SEC,
                                      riferimento=_rif_breve)
            except Exception:
                _ris = []
        st.session_state["risultati"] = _ris
        st.session_state["query_usate"] = [_q]
        st.session_state["scelta"] = None
        st.rerun()

    with st.expander("Le interpretazioni che ho trovato (esposizioni, studi, prediche)"):
        html(
            '<div class="note">Ordinate per <b>affinità al tuo versetto</b>: '
            'prima chi parla proprio di <b>quel</b> versetto, poi chi ne parla '
            'meglio e ha più ascolti. Ogni riga mostra <b>canale</b>, '
            '<b>durata</b> e <b>visualizzazioni</b>.'
            '</div>',
        )
        _interp_list = studio.get("interpretazioni", [])
        # il video con piu' ascolti (badge reale, non finto)
        _idx_top = 0
        _max_v = 0
        for _k, _rr in enumerate(_interp_list):
            _vv = getattr(_rr, "visualizzazioni", 0) or 0
            if _vv > _max_v:
                _max_v = _vv
                _idx_top = _k
        for i, r in enumerate(_interp_list, start=1):
            with st.container(border=True):
                _v = getattr(r, "visualizzazioni", 0)
                _badge = f'#{i}'
                if i == 1 and _interp_list:
                    _badge += " &bull; <b>LA PIU&#39; ADATTA AL TUO VERSETTO</b>"
                elif (i - 1) == _idx_top and _max_v > 0 and i != 1:
                    _badge += " &bull; <b>LA PIU&#39; ASCOLTATA</b>"
                html(
                    f'<div class="badge">{_badge}</div>'
                    f'<div class="card-title">{esc(r.titolo)}</div>'
                    f'<div class="card-meta">{esc(r.canale)}'
                    + (f' &bull; {esc(r.durata)}' if r.durata else "")
                    + (f' &bull; {_v:,}'.replace(",", ".") + " visualizzazioni"
                       if _v else "")
                    + '</div>')
                c1, c2 = st.columns(2)
                with c1:
                    blocco_copia(r.titolo, f"interp{i}")
                with c2:
                    st.link_button("\U0001F3A7 Ascolta", r.url, use_container_width=True)

                chiave_tr = f"tr_{r.video_id}"
                if st.session_state.get(chiave_tr):
                    with st.expander("\U0001F4C4 Leggi la spiegazione scritta (testo integrale)"):
                        _tr = st.session_state[chiave_tr]
                        html(
                            f'<div class="box">{esc(_tr)}</div>')
                        st.download_button(
                            "\U0001F4E4 Scarica (.txt)",
                            data=_tr,
                            file_name=f"spiegazione_{r.video_id}.txt",
                            mime="text/plain",
                            key=f"dl_{r.video_id}",
                        )
                else:
                    if st.button("\U0001F4C4 Leggi la spiegazione scritta",
                                 key=f"leggi_{r.video_id}",
                                 use_container_width=True):
                        with st.spinner("Scarico la trascrizione..."):
                            _t = estrai_spiegazione(r.video_id)
                        if _t:
                            st.session_state[chiave_tr] = _t["testo"]
                        else:
                            st.warning("Questo video non ha una trascrizione disponibile.")

    # ---- MODI PER AVERE L'INTERPRETAZIONE ----
    _prompt_attuale = PROMPT_INTERPRETAZIONE.format(
        riferimento=studio.get("riferimento", {}).get("riferimento", ""),
        testo_versetto=(v.get("testo_pulito", "") + "\n\n"),
    )
    st.markdown("#### Da dove vuoi l'interpretazione?")

    c_m1, c_m2, c_m3 = st.columns(3)
    with c_m1:
        if st.button("\U0001F9E0 Scrivi l'interpretazione con l'IA",
                     key="ia_gratis", use_container_width=True,
                     help="L'app scrive l'interpretazione come un maestro della "
                          "Scrittura: con la chiave Google Gemini (gratis) se "
                          "l'hai messa in alto, altrimenti con l'IA gratuita "
                          "senza chiave. Parti sempre dal testo del TUO "
                          "versetto, quindi e' diversa per ogni passaggio."):
            st.session_state["_ia_richiesta"] = "gratis"
    with c_m2:
        if st.button("\U0001F4AC Chiedi a ChatGPT",
                     key="ia_link", use_container_width=True,
                     help="Copia il prompt e apre ChatGPT (o la tua IA sul "
                          "telefono) gia' pronto."):
            st.session_state["_ia_richiesta"] = "link"
    with c_m3:
        if st.button("\U0001F9E0 Interpreta con ChatGPT",
                     key="ia_api", use_container_width=True,
                     help="Usa la tua chiave API OpenAI (se inserita)."):
            st.session_state["_ia_richiesta"] = "api"
    html(
        "<div class=\"note\">Nella casella qui sotto puoi anche incollare "
        "l'interpretazione che ti ha dato un'altra IA.</div>")

    if st.session_state.get("_ia_richiesta") == "gratis":
        st.session_state["_ia_richiesta"] = None
        with st.spinner("\U0001F9E0 Sto scrivendo l'interpretazione "
                        "(come un maestro della Scrittura)..."):
            _ris = _chiedi_ia(
                _prompt_attuale,
                chiave_gemini=_chiave_gemini_attiva(),
                chiave_openai=st.session_state.get("chiave_ia", ""))
        if _ris.get("errore") and not _ris.get("testo"):
            st.warning(f"IA non disponibile: {_ris['errore']}")
            st.info("Nessun problema: l'app usa comunque lo studio del versetto "
                    "e le predicazioni reali che ha trovato su YouTube.")
        elif _ris.get("testo"):
            _kw = parole_chiave_dall_ia(_ris["testo"], 3)
            if not _kw:
                _kw = estrai_parole_chiave_spirituali(_ris["testo"])[:3]
            st.session_state["versetto_studio"]["interpretazione"] = {
                "testo": _ris["testo"],
                "parole_chiave": _kw,
                "fonte": _ris.get("fonte", "IA"),
                "riferimento": studio.get("riferimento", {}).get("riferimento", ""),
            }
            if st.session_state.get("auto_riflessione", True):
                with st.spinner("\U0001F9E0 Rifaccio la riflessione e la "
                                "riduzione per TikTok..."):
                    _rigenera_riflessione(
                        testo_versetto=(v.get("testo_pulito", "") or ""),
                        interpretazione=_ris["testo"],
                        riferimento=studio.get("riferimento", {}).get(
                            "riferimento", ""))
            st.rerun()

    if st.session_state.get("_ia_richiesta") == "api":
        st.session_state["_ia_richiesta"] = None
        with st.spinner("Sto chiedendo all'IA..."):
            _ris = interpreta_con_ia(_prompt_attuale, chiave=_chiave_ia)
        if _ris.get("errore"):
            st.warning(_ris["errore"])
            st.info("Nessun problema: l'app usa comunque le predicazioni reali "
                    "che ha trovato su YouTube.")
        elif _ris.get("testo"):
            from studio_biblico import estrai_parole_chiave_spirituali
            st.session_state["versetto_studio"]["interpretazione"] = {
                "testo": _ris["testo"],
                "parole_chiave": estrai_parole_chiave_spirituali(_ris["testo"])[:3],
                "fonte": _ris.get("fonte", "ChatGPT (API)"),
                "riferimento": studio.get("riferimento", {}).get("riferimento", ""),
            }
            if st.session_state.get("auto_riflessione", True):
                with st.spinner("\U0001F9E0 Rifaccio la riflessione e la "
                                "riduzione per TikTok..."):
                    _rigenera_riflessione(
                        testo_versetto=(v.get("testo_pulito", "") or ""),
                        interpretazione=_ris["testo"],
                        riferimento=studio.get("riferimento", {}).get(
                            "riferimento", ""))
            st.rerun()

    if st.session_state.get("_ia_richiesta") == "link":
        st.session_state["_ia_richiesta"] = None
        blocco_copia(_prompt_attuale, "copia_prompt_ia",
                     "\U0001F4CB Copia il prompt")
        st.link_button("\U0001F4AC Apri ChatGPT con il prompt",
                       link_chatgpt(_prompt_attuale), use_container_width=True)
        html(
            "<div class=\"note\">Incolla qui sotto la risposta dell'IA e premi "
            '"Usa questa interpretazione": l\'app ci mette dentro le 3 parole '
            "chiave e rifiinisce la ricerca della canzone.</div>")

    _incollata = st.text_area(
        "Incolla qui l'interpretazione",
        value=st.session_state.get("_interp_incollata", ""),
        height=140,
        key="interp_incollata_area",
    )
    if st.button("\U0001F50D Usa questa interpretazione",
                 use_container_width=True):
        if _incollata.strip():
            from studio_biblico import estrai_parole_chiave_spirituali
            _kw = estrai_parole_chiave_spirituali(_incollata)[:3]
            st.session_state["versetto_studio"]["interpretazione"] = {
                "testo": _incollata,
                "parole_chiave": _kw,
                "fonte": "la tua IA",
                "riferimento": studio.get("riferimento", {}).get("riferimento", ""),
            }
            if st.session_state.get("auto_riflessione", True):
                with st.spinner("\U0001F9E0 Rifaccio la riflessione e la "
                                "riduzione per TikTok..."):
                    _rigenera_riflessione(
                        testo_versetto=(v.get("testo_pulito", "") or ""),
                        interpretazione=_incollata,
                        riferimento=studio.get("riferimento", {}).get(
                            "riferimento", ""))
            st.session_state["_ria_fase2"] = True
            st.rerun()

    with st.expander("Il prompt per l'interpretazione (per ChatGPT, ecc.)"):
        _prompt = PROMPT_INTERPRETAZIONE.format(
            riferimento=studio.get("riferimento", {}).get("riferimento", ""),
            testo_versetto=(v.get("testo_pulito", "") + "\n\n"),
        )
        st.code(_prompt, language="text")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            blocco_copia(_prompt, "copia_prompt",
                         "\U0001F4CB Copia il prompt")
        with col_p2:
            st.link_button(
                "\U0001F4AC Apri ChatGPT",
                "https://chatgpt.com/",
                use_container_width=True,
            )

    # ======================================================================
    # FASE 1b - LA RIFLESSIONE (scritta dall'IA) + IL POST TIKTOK
    # ======================================================================
    # L'interpretazione spiega il versetto. Qui l'IA fa un passo oltre:
    # scrive una RIFLESSIONE personale su quella interpretazione e la
    # RIDUCE in un post pronto per TikTok (hook, corpo, caption, CTA).
    _rif_ia = st.session_state.get("riflessione_ia") or {}
    _post_ia = _rif_ia.get("post") or {}

    html(
        '<hr><div class="step">FASE 1b</div>'
        "<h3>\U0001F4DD La riflessione e il post pronti</h3>"
        '<div class="note">L\'IA prende l\'interpretazione di sopra e ne fa '
        'una <b>riflessione personale</b> (come se la scrivesse il creator), '
        'poi la <b>riduce</b> in un post TikTok: la frase da mettere a '
        'schermo, 3 righe da dire e la caption. Tocca il pulsante e in un '
        'colpo sola hai tutto il materiale del post.</div>')

    _c_rif1, _c_rif2 = st.columns(2)
    with _c_rif1:
        if st.button("\U0001F9E0 Fai la riflessione + il post",
                     type="primary", use_container_width=True,
                     key="fai_riflessione_ia",
                     help="L'IA scrive la riflessione sul versetto e la "
                          "riduce subito in un post pronto per TikTok. "
                          "Ci mette 15-40 secondi."):
            with st.spinner("\U0001F9E0 Sto scrivendo la riflessione e "
                            "riducendola per TikTok..."):
                _esito = genera_riflessione_e_post(
                    testo_versetto=(v.get("testo_pulito", "") or ""),
                    interpretazione=(interp.get("testo", "") or ""),
                    riferimento=studio.get("riferimento", {}).get(
                        "riferimento", ""),
                    chiave_gemini=_chiave_gemini_attiva(),
                    chiave_openai=st.session_state.get("chiave_ia", ""))
            _salva_riflessione_ia(_esito.get("riflessione", ""),
                                  _esito.get("post", {}),
                                  _esito.get("parole_chiave", []),
                                  _esito.get("fonte", "IA"))
            st.session_state["_rif_ia_fatto"] = True
            st.rerun()
    with _c_rif2:
        if st.button("\U0001F50D Riduci la mia riflessione in un post",
                     use_container_width=True, key="riduci_riflessione_ia",
                     help="Usa la riflessione che hai scritto tu (o quella "
                          "dell'IA) e ricavane il post per TikTok."):
            _mia = (st.session_state.get("riflessione_ia_testo") or
                    _rif_ia.get("riflessione", "")).strip()
            if not _mia:
                st.warning("Prima scrivi o fai generare la riflessione "
                           "\U0001F4D8")
            else:
                with st.spinner("\U0001F50D Riduco la riflessione per "
                                "TikTok..."):
                    _esito2 = riduci_per_post(
                        _mia,
                        testo_versetto=(v.get("testo_pulito", "") or ""),
                        riferimento=studio.get("riferimento", {}).get(
                            "riferimento", ""),
                        chiave_gemini=_chiave_gemini_attiva(),
                        chiave_openai=st.session_state.get("chiave_ia", ""))
                _esito2 = dict(_esito2)
                _salva_riflessione_ia(_mia, _esito2,
                                      _rif_ia.get("parole_chiave", []),
                                      _esito2.get("fonte", "IA"))
                st.rerun()

    if _rif_ia.get("errore") and not _rif_ia.get("riflessione"):
        st.info("L'IA non ha risposto (" + str(_rif_ia["errore"])[:160] +
                "). La riflessione viene presa direttamente dall'interpretazione.")

    if _rif_ia.get("riflessione"):
        # ---- LA RIFLESSIONE ----
        html(
            '<div class="step">LA RIFLESSIONE</div>'
            f'<div class="note">Scritta da: <b>{esc(_rif_ia.get("fonte", "IA"))}'
            '</b> &bull; <b>tu</b> puoi correggerla: il pulsante "Riduci la '
            'mia riflessione" usa il testo che trovi qui sotto.</div>')
        _rif_testo = st.text_area(
            "La riflessione (modificabile)",
            value=(st.session_state["riflessione_ia_testo"]
                   if "riflessione_ia_testo" in st.session_state
                   else _rif_ia.get("riflessione", "")),
            height=190, key="riflessione_ia_testo",
        )
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            blocco_copia(_rif_testo, "copia_riflessione",
                         "\U0001F4CB Copia la riflessione")
        with col_r2:
            st.download_button(
                "\U0001F4E4 Scarica (.txt)", data=_rif_testo,
                file_name=f"riflessione_{v.get('riferimento', 'versetto')}"
                          .replace(" ", "_").replace(",", "-")
                          .replace(":", "-") + ".txt",
                mime="text/plain", key="dl_riflessione")

    if _post_ia.get("hook") or _post_ia.get("caption"):
        # ---- IL POST TIKTOK ----
        _mostra_post_ia(_post_ia, "ia")

        # ---- USALO NEL POST ----
        if st.button("\U0001F4E4 Usa questo post per il mio TikTok",
                     type="primary", use_container_width=True,
                     key="usa_post_ia"):
            _post_gia = st.session_state.get("post")
            if not _post_gia:
                st.info("Prima scegli la canzone (pulsante "
                        "'\u2B50 Scegli questa canzone per il post'): poi "
                        "torna qui e usa la caption dell'IA.")
            else:
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
                    st.session_state["hook"] = _post_ia["hook"]
                st.success("\u2705 Fatto: nel PASSAGGIO 3 trovi la caption e "
                           "il testo a schermo scritti dall'IA.")


# --------------------------------------------------------------------------
# I versetti biblici trovati (dal pulsante "Trova il testo adatto")
# --------------------------------------------------------------------------

versetti = st.session_state.get("versetti") or []
if versetti:
    _da_riflessione = bool(st.session_state.get("riflessione_giornaliera")) and \
        st.session_state.get("versetti_da_riflessione")
    _titolo_blocco = ("\U0001F4DD Versetti che parlano alla TUA riflessione"
                      if _da_riflessione else
                      "\U0001F4D6 Versetti che parlano al tuo pensiero")
    _nota_blocco = ("Scegli il versetto che ti risuona: l\'app lo mette nella "
                    "casella e cerca subito la canzone. La tua riflessione "
                    "diventa la caption del post."
                    if _da_riflessione else
                    "Scegli il versetto che ti risuona: l\'app lo mette nella "
                    "casella e cerca subito la canzone.")
    html(
        '<div class="step">Il testo biblico</div>'
        f'<h3>{_titolo_blocco}</h3>'
        f'<div class="note">Testo di riferimento: {esc(NOME_TRADUZIONE)}. '
        f'{_nota_blocco}</div>')
    for i, v in enumerate(versetti, start=1):
        with st.container(border=True):
            chip = "".join(f'<span class="chip">{esc(t)}</span>' for t in v["temi"])
            _scelta_ia = (st.session_state.get("scelta_ia_versetto") or {})
            _scelto = (_scelta_ia.get("indice") == i - 1) or (
                bool(_scelta_ia.get("riferimento")) and i == 1)
            _badge_ia = ('<span class="chip" style="background:#fde68a;color:#92400e;'
                         'font-weight:700">&#127775; scelto dall\'IA</span> ') \
                if _scelto else ""
            _badge_esatto = ('<span class="chip" style="background:#bbf7d0;'
                             'color:#065f46;font-weight:700">&#9989; esatto: '
                             'e\' quello che hai scritto</span> ') \
                if v.get("esatto") else ""
            html(
                f'<div class="badge">#{i}</div>'
                f'<div class="card-title">{esc(v["riferimento"])}</div>'
                f'<div class="card-meta" style="font-size:.92rem;opacity:.85;">'
                f'«{esc(v["testo"])}»</div>{chip}{_badge_esatto}{_badge_ia}')
            if _scelto and _scelta_ia.get("motivo"):
                html(
                    '<div class="note box-ok"><b>Perche\' questo:</b> '
                    f'{esc(_scelta_ia["motivo"])}</div>')
            col_a, col_b = st.columns(2)
            with col_a:
                st.button(
                    "\u2705 Usa questo testo",
                    key=f"usa_versetto_{i}",
                    use_container_width=True,
                    on_click=_imposta_testo,
                    args=(v["testo"],),
                )
            with col_b:
                st.button(
                    "\U0001F50E Trova la canzone",
                    key=f"canzone_versetto_{i}",
                    use_container_width=True,
                    on_click=_imposta_testo,
                    args=(v["testo"],),
                )

# --------------------------------------------------------------------------
# Studio biblico: i 4 passi + le interpretazioni dei pastori
# --------------------------------------------------------------------------

riferimento = st.session_state.get("riferimento")
if riferimento is None and st.session_state.get("analisi"):
    riferimento = rileva_riferimento(st.session_state["analisi"].get("testo", "")) \
        or rileva_riferimento(testo)

if riferimento:
    with st.expander("\U0001F4D6 Studio biblico del versetto (i 4 passi)"):
        html(
            f'<div class="box"><b>Riferimento rilevato:</b> {esc(riferimento["riferimento"])}'
            f'<br><span class="note">Versione inglese per le ricerche: '
            f'{esc(riferimento["riferimento_en"])}</span></div>')
        for passo in genera_passi(testo, st.session_state["analisi"], riferimento):
            html(
                f'<div class="box" style="margin-bottom:8px;">'
                f'<b>{esc(passo["titolo"])}</b><br>{esc(passo["contenuto"])}<br>'
                f'<span class="note"><i>Domanda guida: {esc(passo["domanda"])}</i></span>'
                f'</div>')

        query_st = query_studio(riferimento, testo)
        if st.button("\U0001F50D Cerca le interpretazioni (studio/esposizione su YouTube)",
                     use_container_width=True):
            with st.spinner("\U0001F50D Cerco gli insegnamenti..."):
                try:
                    st.session_state["studio_risultati"] = ricerca_cached(
                        tuple(query_st), 4, tuple(estrai_parole_chiave(testo, 2)))
                except Exception as exc:
                    st.error(f"\u26A0\uFE0F {exc}")
                    st.session_state["studio_risultati"] = []

        for i, r in enumerate(st.session_state.get("studio_risultati", []), start=1):
            with st.container(border=True):
                html(
                    f'<div class="card-title">{esc(r.titolo)}</div>'
                    f'<div class="card-meta">{esc(r.canale)}'
                    + (f' &bull; {esc(r.durata)}' if r.durata else "") + '</div>')
                c1, c2 = st.columns(2)
                with c1:
                    blocco_copia(r.titolo, f"studio{i}")
                with c2:
                    st.link_button("\U0001F3A7 Ascolta", r.url, use_container_width=True)

# PASSAGGIO 2 - CERCA SU TIKTOK (il titolo da usare)
# ==========================================================================

# il titolo da cercare su TikTok: le parole chiave spirituali del versetto
_parole_tiktok = []
try:
    _interp2 = (st.session_state.get("versetto_studio") or {}).get("interpretazione") or {}
    _parole_tiktok = _interp2.get("parole_chiave") or []
except Exception:
    _parole_tiktok = []
if not _parole_tiktok:
    _parole_tiktok = estrai_parole_chiave(testo or "", 3)
_query_tiktok = " ".join(_parole_tiktok[:3]).strip() or (testo or "").strip()[:60]

html('<hr>')
html(
    '<div class="step">PASSAGGIO 2</div>'
    '<h3>\U0001F50D Il titolo da cercare su TikTok</h3>')
html(
    '<div class="note box-ok"><b>Perche\' questo titolo?</b> L\'app lo ricava '
    'dall\'interpretazione del tuo versetto: sono le parole spirituali che '
    'parlano del cuore del passaggio. Su TikTok cerca <b>questo titolo</b> '
    'nella libreria audio e trovi il suono originale.</div>')
html(
    f'<div class="box"><b>Titolo da cercare:</b> {esc(_query_tiktok)}</div>')
blocco_copia(_query_tiktok, "copia_titolo_tiktok",
             "\U0001F4CB Copia il titolo per TikTok")
st.link_button(
    "\U0001F50A Cerca questo titolo su TikTok",
    f"https://www.tiktok.com/search?q={_quote_url(_query_tiktok)}",
    use_container_width=True,
    type="primary")
st.caption("Si apre la ricerca di TikTok: da li' scegli il suono originale "
           "(non il video di un altro). Se TikTok ti manda alla home, "
           "accedi col tuo account e riprova il link.")
html(
    '<div class="note" style="margin-top:8px;">'
    '<b>Il percorso completo (5 secondi):</b><br>'
    '1) tocca "Copia il titolo per TikTok" (il titolo e\' negli appunti)<br>'
    '2) apri TikTok sul telefono &rarr; tocca "+" (nuovo video)<br>'
    '3) "Aggiungi suono" &rarr; incolla il titolo &rarr; scegli il suono<br>'
    '4) registra il video con quel suono e pubblica.<br><br>'
    '<b>Se non vuoi cercare niente:</b> vai qui sotto in "Crea una canzone '
    'ORIGINALE" &rarr; "FAI TUTTO": l\'app ti prepara tutto (parole, '
    'canzone cantata, poster, video 9:16) e tu pubblichi.</div>')

# ==========================================================================
# ---- CANZONE ORIGINALE: testo + musica + video TikTok ----
with st.expander("\U0001F3B6 Crea una canzone ORIGINALE per il tuo post"):
    html(
        '<div class="note">Oltre alle canzoni che trovo su YouTube, '
        'posso <b>comporre una canzone nuova</b> per il tuo versetto: '
        "l'IA scrive il testo, il motore musicale lo canta, e l'app ci "
        'mette sopra uno sfondo per fare un <b>video .mp4 pronto da '
        'caricare su TikTok</b> (un brano tuo: nessun problema di '
        'copyright).<br><br>'
        'Per la canzone cantata servono i tuoi crediti gratuiti di '
        'Suno (le istruzioni sono nella barra laterale) oppure un '
        'modello open source.</div>')
    html('<div class="note" style="opacity:.75">Motori disponibili: '
         '<b>ACE-Step</b> (open source: canta il brano e l\'audio si '
         'scarica, tutto automatico), <b>Suno</b> (i crediti gratuiti del tuo '
         'account), <b>MusicGen</b> (strumentale), <b>Treblo</b> (chiede la '
         'carta). <b>Niente pagamenti, niente carte</b> per usare l\'app.</div>')

    _stile = st.text_input(
        "Stile musicale", value=STILE_DEFAULT, key="stile_musica",
        help="Descrivi come dev'essere la canzone (il motore lo usa "
             "come 'prompt'). Es. 'inno pentecostale, voce maschile, "
             "piano e cori soft, 78 BPM'.")

    # --- la chiave del motore, QUI dentro (basta metterla una volta) ---
    with st.container(border=True):
        html('<div class="note box-ok"><b>\U0001F3A7 Per far cantare il '
             'brano</b> ti serve la chiave di <b>Treblo</b>: e gratis '
             '(3.000 crediti = 30 canzoni) e resta nel TUO browser, non '
             'finisce sul server e non la vede nessun altro.</div>')
        _kc1, _kc2 = st.columns([3, 1])
        with _kc1:
            _chiave_qua = st.text_input(
                "Chiave Treblo (incolla qui)",
                type="password",
                placeholder="sk_...",
                help="La prendi su treblo.com -> account sviluppatore. "
                     "Resta nel tuo browser: non passa dalla chat.",
                key="chiave_treblo_sezione",
            )
        with _kc2:
            st.link_button(
                "Prendila gratis \u2197",
                "https://treblo.com/developers/account",
                use_container_width=True)
            if st.button("\U0001F50E Verifica",
                         use_container_width=True, key="verifica_treblo_sezione"):
                _ok, _nota = treblo_disponibile(_chiave_qua)
                (st.success if _ok else st.error)(_nota)
        if _chiave_qua:
            html(_SCRIPT_SALVA_TREBLO.replace("__CHIAVE__", _chiave_qua),
                 js=True)
        else:
            html(_SCRIPT_LEGGI_TREBLO, js=True)

    # --- 1) il testo della canzone ---
    _b1, _b2 = st.columns(2)
    with _b1:
        if st.button("\U0001F3A4 Scrivi il testo della canzone",
                     use_container_width=True, key="scrivi_testi"):
            _rif = (st.session_state.get("riferimento") or {})
            _riferimento = _rif.get("riferimento", "")
            _interp = (studio.get("interpretazione") or {}).get("testo", "")
            with st.spinner("L'IA sta scrivendo il testo del brano..."):
                _res = scrivi_testi_canzone(
                    _riferimento or (testo or "")[:120], _interp,
                    temi=", ".join((st.session_state["analisi"] or {})
                                  .get("temi", [])[:3]),
                    chiave_gemini=_chiave_gemini_attiva(),
                    chiave_openai=st.session_state.get("chiave_ia", ""))
            if _res.get("ok"):
                st.session_state["canzone_testi"] = _res["testo"]
            else:
                st.warning(_res.get("errore", ""))
    with _b2:
        _motore = st.selectbox(
            "Motore musicale", list(MOTORI_GRATUITI), key="motore_scelto",
            help="Suno usa i crediti gratuiti giornalieri del TUO account "
                 "(serve il servizio open source attivo + il cookie). "
                 "ACE-Step e MusicGen sono open source e gratis, ma hanno "
                 "coda: possono mettersi in attesa.")
    # --- 2) i tag di stile (sempre disponibili) ---
    _tag_finali = st.text_input(
        "Tag di stile (invio quelli che mi hai dato)",
        value=TUTTI_I_TAG, key="tag_musica",
        help="Stile: Modern Christian Worship, contemporary gospel, "
             "inspiring, uplifting, powerful vocal harmony. "
             "Strumenti: acoustic guitar, ambient piano, cinematic "
             "synths, build-up drums, emotional strings.")

    # --- IL PULSANTE UNICO: fa tutto, in un colpo ---
    if st.button("\U0001F3AC FAI TUTTO: parole + canzone + poster + video",
                 type="primary", use_container_width=True, key="fai_tutto"):
        _rif = (st.session_state.get("riferimento") or {})
        _riferimento = _rif.get("riferimento", "")
        _interp = (studio.get("interpretazione") or {}).get("testo", "")
        _rif_gr = st.session_state.get("riflessione_giornaliera") or ""
        # 1) le parole
        if not st.session_state.get("canzone_testi"):
            with st.spinner("1 di 4 - L'IA sta scrivendo le parole del "
                            "brano..."):
                if _rif_gr:
                    try:
                        from testi_canzone import scrivi_testi_da_riflessione
                        _res_t = scrivi_testi_da_riflessione(
                            _rif_gr, riferimento=_riferimento,
                            testo_versetto=(studio.get("versetto") or {}).get(
                                "testo", ""),
                            temi=", ".join(estrai_parole_chiave(_rif_gr, 3)),
                            chiave_gemini=_chiave_gemini_attiva(),
                            chiave_openai=st.session_state.get("chiave_ia", ""))
                    except Exception as _exc:
                        _res_t = {"ok": False, "errore": str(_exc)[:120]}
                else:
                    _res_t = scrivi_testi_canzone(
                        _riferimento or (testo or "")[:120], _interp,
                        temi=", ".join((st.session_state["analisi"] or {})
                                      .get("temi", [])[:3]),
                        chiave_gemini=_chiave_gemini_attiva(),
                        chiave_openai=st.session_state.get("chiave_ia", ""))
            if not _res_t.get("ok"):
                st.error(_res_t.get("errore", "Non sono riuscito a scrivere "
                                                 "le parole del brano."))
                st.stop()
            st.session_state["canzone_testi"] = _res_t["testo"]
        # 2) la musica
        with st.spinner("2 di 4 - Il motore musicale sta componendo il "
                        "brano (1-3 minuti)..."):
            _res_m = _genera_musica(
                _motore, struttura_canzone(st.session_state["canzone_testi"]),
                _tag_finali, _stile)
        if not _res_m.get("ok"):
            st.error(_res_m.get("errore", "Composizione fallita."))
            if _res_m.get("protegto"):
                st.session_state["suno_protegto"] = True
            st.stop()
        st.session_state["canzone_audio"] = _res_m["file"]
        st.session_state["canzone_audio_url"] = _res_m.get("url", "")
        st.session_state["canzone_modello"] = _res_m.get("motore", "")
        # 3) il POSTER: l'immagine che l'AI disegna sul versetto
        _poster = ""
        with st.spinner("3 di 4 - Sto disegnando il poster del post..."):
            _res_img = genera_immagine(
                versetto=(studio.get("versetto") or {}).get("testo_pulito", "")
                or (testo or "")[:300],
                tema=", ".join((st.session_state["analisi"] or {}).get(
                    "temi", [])[:2]),
                stile="Caldo e speranza",
                chiave_gemini=_chiave_gemini_attiva())
        if _res_img.get("ok"):
            _poster = _res_img["file"]
            st.session_state["immagine_ai"] = _poster
            st.session_state["immagine_ai_fonte"] = _res_img.get("fonte", "")
        # 4) il video: poster + mp3 + testo
        with st.spinner("4 di 4 - Sto montando il video verticale..."):
            _rif_v = ((st.session_state.get("riferimento") or {}).get(
                "riferimento", "") or testo or "")[:160]
            _res_v = crea_video_tiktok(
                _res_m["file"],
                testo=_rif_v,
                sfondo=("foto" if _poster else "immagine"),
                immagine_propria=_poster,
                muovo=True)
        if _res_v.get("ok"):
            st.session_state["canzone_video"] = _res_v["file"]
            st.success("\u2705 \u2705 \u2705 Fatto tutto: parole, canzone, "
                       "poster e video! Il video e' gia' qui sotto.")
        else:
            st.warning("La canzone e' pronta ma il video non e' uscito: "
                       + str(_res_v.get("errore", ""))[:120])
        # il POST (caption, hook, hashtag) viene preparato qui, cosi' non
        # serve scegliere una canzone su YouTube per avere la caption
        _post_esistente = st.session_state.get("post")
        _caption_ia = (st.session_state.get("riflessione_ia") or {}).get(
            "post", {}).get("caption", "")
        if not _post_esistente or not _post_esistente.get("caption"):
            _hashtag = genera_hashtag(testo, parole_chiave)
            _formato = (st.session_state["analisi"] or {}).get(
                "formato_post", "Versetto + domanda")
            _caption = (_caption_ia or genera_caption(testo, _formato, _hashtag))
            _hook = (st.session_state.get("riflessione_ia") or {}).get(
                "post", {}).get("hook", "") or genera_hook(testo)
            st.session_state["post"] = {
                "titolo": "canzone originale sul tuo versetto",
                "video_id": "", "canale": "l'app",
                "hashtag": _hashtag, "formato": _formato,
                "caption": _caption, "hook": _hook,
                "corpo_ia": (st.session_state.get("riflessione_ia") or {}).get(
                    "post", {}).get("corpo", []),
            }
            if _caption:
                st.session_state["caption"] = _caption
            if _hook:
                st.session_state["hook"] = _hook
        st.rerun()

    if st.session_state.get("canzone_testi"):
        _testi_canzone = st.text_area(
            "Il testo della canzone (modificalo come vuoi)",
            value=st.session_state["canzone_testi"], height=220,
            key="campo_testi_canzone")
        st.session_state["canzone_testi"] = _testi_canzone

        # --- 2) la musica ---
        if _motore.startswith("Treblo"):
            _ok_tr, _nota_tr = treblo_disponibile()
            if not _ok_tr:
                st.info("Treblo non e' pronto: " + _nota_tr + " Metti la "
                        "chiave nella barra laterale (campo 'Chiave "
                        "Treblo').")
        if _motore.startswith("Suno"):
            _ok_suno, _nota_suno = suno_disponibile()
            if not _ok_suno:
                st.info("Suno non e' raggiungibile: " + _nota_suno + ". "
                        "Attivalo dalla barra laterale (Espandi > 'Suno: "
                        "i crediti gratuiti del TUO account') oppure "
                        "prova un altro motore qui sotto.")
        if st.button("\U0001F3BC Componi e canta la canzone",
                     use_container_width=True, key="componi_canzone"):
            _testi_finali = struttura_canzone(_testi_canzone)
            _stile_finale = (f"{_stile}, {_tag_finali}" if _stile else
                             _tag_finali)
            with st.spinner("Sto componendo e cantando il brano "
                            "(1-3 minuti, puo' mettersi in coda)..."):
                _res_m = _genera_musica(_motore, _testi_finali, _tag_finali,
                                        _stile)
            if _res_m.get("ok"):
                st.session_state["canzone_audio"] = _res_m["file"]
                st.session_state["canzone_audio_url"] = _res_m.get("url", "")
                st.session_state["canzone_modello"] = _res_m.get("motore", "")
            else:
                st.error(_res_m.get("errore", "Composizione fallita."))
                if _res_m.get("protegto"):
                    st.session_state["suno_protegto"] = True

        # Brano pronto ma protetto da Suno (o un brano tuo): si puo'
        # caricare qui il file audio per fare il video.
        if st.session_state.get("suno_protegto") or (
                not st.session_state.get("canzone_audio")):
            with st.expander("\U0001F3A7 Carica il brano (facoltativo)",
                             expanded=bool(st.session_state.get(
                                 "suno_protegto"))):
                html('<div class="note">Se hai scaricato il brano da '
                     'suno.com (o vuoi usare un brano tuo), caricalo '
                     'qui: l\'app ci fa sopra il video verticale. '
                     'Accetta .mp3, .m4a, .wav.</div>')
                if st.session_state.get("suno_protegto"):
                    st.link_button(
                        "\U0001F3A7 Apri la mia libreria su suno.com",
                        "https://suno.com/library",
                        use_container_width=True)
                _brano = st.file_uploader(
                    "Il brano (file audio)",
                    type=["mp3", "m4a", "wav", "aac", "ogg"],
                    key="brano_caricato")
                if _brano is not None:
                    _dest = os.path.join(tempfile.gettempdir(),
                                         "brano_caricato" +
                                         os.path.splitext(_brano.name)[1])
                    with open(_dest, "wb") as _f:
                        _f.write(_brano.getvalue())
                    st.session_state["canzone_audio"] = _dest
                    st.session_state["canzone_modello"] = "Il tuo brano"
                    st.session_state["suno_protegto"] = False
                    st.success("Brano caricato. Ora fai il video qui sotto.")
                    st.rerun()

        if st.session_state.get("canzone_audio"):
            st.audio(st.session_state["canzone_audio"])
            if st.session_state.get("canzone_modello"):
                html('<div class="note">Motore usato: <b>'
                     + esc(st.session_state["canzone_modello"]) + '</b></div>')
            st.download_button(
                "\U0001F3B5 Scarica la canzone (.mp3)",
                data=open(st.session_state["canzone_audio"], "rb").read(),
                file_name="cantico.mp3", mime="audio/mpeg",
                key="dl_canzone_mp3")

            # --- 3) il video per TikTok ---
            st.markdown("**3. Il video pronto per TikTok** (9:16 verticale)")
            html(
                '<div class="note box-ok"><b>Il post (caption, hashtag, l\'ora) '
                'lo trovi qui:</b> in fondo, nel blocco '
                '<b>"PASSAGGIO 3 - Prepara e pubblica"</b>. L\'app te lo '
                'prepara da sola quando usi "FAI TUTTO" (caption sul tuo '
                'versetto, testo a schermo e le 3 righe). Se hai anche scelto '
                'una canzone su YouTube, la caption viene dalle tue parole '
                'riflessione.</div>', unsafe_allow_html=True)

            # ---- 3a) L'IMMAGINE DEL POST, GENERATA DALL'AI ----
            with st.expander("\U0001F5BC️ Genera l'immagine del post (AI)",
                             expanded=False):
                st.markdown(
                    '<div class="note">L\'AI disegna <b>l\'immagine</b> che '
                    'sta dietro al tuo versetto: cosi\' il post e\' completo '
                    'senza programmi esterni (canzone + immagine + testo).<br>'
                    'Con la chiave Gemini la fa lei; senza, usa il motore '
                    'gratis.</div>', unsafe_allow_html=True)
                _stile_img = st.selectbox(
                    "Che feeling vuoi?",
                    ["Caldo e speranza", "Sereno e contemplativo",
                     "Drammatico e profondo", "Luminoso e gioioso",
                     "Notte e silenzio"],
                    key="stile_immagine")
                if st.button("\U0001F3A8 Genera l'immagine",
                             use_container_width=True, key="genera_immagine"):
                    with st.spinner("\U0001F3A8 Sto disegnando l'immagine "
                                    "del post..."):
                        _ris_img = genera_immagine(
                            versetto=(v.get("testo_pulito", "") or testo or "")[:300],
                            tema=", ".join((st.session_state["analisi"] or {})
                                           .get("temi", [])[:2]),
                            stile=_stile_img,
                            chiave_gemini=_chiave_gemini_attiva())
                    if _ris_img.get("ok"):
                        st.session_state["immagine_ai"] = _ris_img["file"]
                        st.session_state["immagine_ai_fonte"] = _ris_img.get(
                            "fonte", "")
                        st.success("\u2705 Immagine pronta!")
                    else:
                        st.error("Non sono riuscito a generarla: "
                                 + str(_ris_img.get("errore", ""))[:150])
            if st.session_state.get("immagine_ai"):
                _img_ai = st.session_state["immagine_ai"]
                st.image(_img_ai, width=260)
                st.caption("Immagine generata dall'AI"
                           + (f" ({st.session_state.get('immagine_ai_fonte','')})"
                              if st.session_state.get("immagine_ai_fonte")
                              else ""))
                with open(_img_ai, "rb") as _f:
                    st.download_button(
                        "\U0001F5BC️ Scarica l'immagine", data=_f.read(),
                        file_name="cantico_immagine.png",
                        mime="image/png", key="dl_immagine_ai")

            _v1, _v2 = st.columns(2)
            with _v1:
                _opzioni_sfondo = ["immagine", "nero", "foto"]
                if st.session_state.get("immagine_ai"):
                    _opzioni_sfondo.insert(0, "AI")
                _sfondo = st.radio(
                    "Sfondo", _opzioni_sfondo,
                    key="sfondo_video", horizontal=True,
                    help="AI: l'immagine generata dall'AI. immagine: sfondo "
                         "a gradiente con il testo del verso. nero: tela nera "
                         "con la scritta. foto: carica una tua immagine.")
            with _v2:
                _foto = ""
                if _sfondo == "foto":
                    _foto = st.file_uploader("La tua immagine",
                                             type=["jpg", "jpeg", "png"],
                                             key="foto_video")
                _muovo = st.checkbox(
                    "Loop animato (leggero zoom)", value=True,
                    key="loop_animato",
                    help="Attivo: l'immagine si muove lentamente, "
                         "come un video. Disattivo: immagine fissa.")
            if st.button("\U0001F3AC Fai il video per TikTok",
                         use_container_width=True, key="fai_video"):
                _img = ""
                if _sfondo == "AI" and st.session_state.get("immagine_ai"):
                    _img = st.session_state["immagine_ai"]
                elif _foto is not None:
                    _img = os.path.join(tempfile.gettempdir(),
                                        "foto_cantico.jpg")
                    with open(_img, "wb") as _f:
                        _f.write(_foto.getvalue())
                with st.spinner("Sto montando il video..."):
                    _res_v = crea_video_tiktok(
                        st.session_state["canzone_audio"],
                        testo=(v.get("riferimento", "") or testo or "")[:160],
                        sfondo=("foto" if _sfondo == "AI" else _sfondo),
                        immagine_propria=_img,
                        muovo=_muovo)
                if _res_v.get("ok"):
                    st.session_state["canzone_video"] = _res_v["file"]
                else:
                    st.error(_res_v.get("errore", "Video non creato."))
            if st.session_state.get("canzone_video"):
                st.video(st.session_state["canzone_video"])
                with open(st.session_state["canzone_video"], "rb") as _f:
                    _dati_v = _f.read()
                st.download_button(
                    "\U0001F3AC Scarica il video per TikTok (.mp4)",
                    data=_dati_v, file_name="cantico_tiktok.mp4",
                    mime="video/mp4", key="dl_video_mp4")
            else:
                # ---- VIDEO SOLO POSTER + VERSETTO (senza canzone) ----
                with st.expander("\U0001F5BC️ Solo poster + versetto (senza "
                                 "canzone)"):
                    html(
                        '<div class="note">Se vuoi solo il <b>poster con il '
                        'versetto</b> (senza la canzone), l\'app genera un '
                        'video breve e silenzioso. Poi su TikTok aggiungi tu '
                        'il suono (dalla libreria audio) e pubblichi.</div>',
                        unsafe_allow_html=True)
                    if st.button("\U0001F5BC️ Genera il video (solo poster)",
                                 use_container_width=True,
                                 key="genera_video_silenzioso"):
                        _img = st.session_state.get("immagine_ai") or ""
                        if not _img:
                            with st.spinner("Sto disegnando il poster..."):
                                _ris_img = genera_immagine(
                                    versetto=(v.get("testo_pulito", "") or
                                              testo or "")[:300],
                                    tema=", ".join(
                                        (st.session_state["analisi"] or {})
                                        .get("temi", [])[:2]),
                                    stile="Caldo e speranza",
                                    chiave_gemini=_chiave_gemini_attiva())
                            if _ris_img.get("ok"):
                                _img = _ris_img["file"]
                                st.session_state["immagine_ai"] = _img
                                st.session_state["immagine_ai_fonte"] = _ris_img.get(
                                    "fonte", "")
                            else:
                                st.error("Non sono riuscito a generare il "
                                         "poster: " + str(
                                             _ris_img.get("errore", ""))[:120])
                        if _img:
                            with st.spinner("Sto montando il video..."):
                                _res_vs = crea_video_silenzioso(
                                    testo=(v.get("riferimento", "") or testo or "")[:160],
                                    immagine=_img, durata=8)
                            if _res_vs.get("ok"):
                                st.session_state["canzone_video"] = _res_vs["file"]
                                st.success("\u2705 Video pronto (silenzioso). "
                                           "Ora scegli il suono su TikTok.")
                                st.rerun()
                            else:
                                st.error("Video non creato: "
                                         + str(_res_vs.get("errore", ""))[:150])
                    if st.session_state.get("immagine_ai"):
                        st.image(st.session_state["immagine_ai"], width=240)
                        with open(st.session_state["immagine_ai"], "rb") as _f:
                            st.download_button(
                                "\U0001F5BC️ Scarica il poster (.png)",
                                data=_f.read(), file_name="cantico_poster.png",
                                mime="image/png", key="dl_poster_silenzioso")

                # ---- PUBBLICA TUTTO CON UN TOCCO ----
                # se il tuo TikTok e' collegato, l'app manda video + caption
                # da sola: non devi aprire TikTok
                try:
                    import tiktok_pubblica as _tkpub2
                    _token2 = _tkpub2.token_utente()
                except Exception:
                    _tkpub2 = None
                    _token2 = ""
                if _tkpub2 and _token2:
                    with st.container(border=True):
                        st.markdown("**\U0001F4E4 Pubblica tutto con un tocco**")
                        st.markdown(
                            '<div class="note">Il tuo TikTok è collegato: '
                            'l\'app manda il video con la caption già scritta. '
                            'Non devi aprire TikTok.</div>',
                            unsafe_allow_html=True)
                        _priv2 = st.selectbox(
                            "Chi può vederlo?",
                            ["PUBLIC_TO_EVERYONE", "SELF_ONLY",
                             "MUTUAL_FOLLOW_FRIENDS"],
                            format_func=lambda x: _tkpub2.PRIVACY.get(x, x),
                            key="privacy_una_tocca")
                        _cap2 = ""
                        _post2 = st.session_state.get("post") or {}
                        if _post2.get("caption"):
                            _cap2 = _post2["caption"]
                        else:
                            _hashtag2 = genera_hashtag(testo, parole_chiave)
                            _cap2 = genera_caption(
                                testo, (st.session_state["analisi"] or {}).get(
                                    "formato_post", "Versetto + domanda"),
                                _hashtag2)
                        if st.button("\U0001F4E4 Pubblica adesso", type="primary",
                                     use_container_width=True,
                                     key="pubblica_una_tocca"):
                            with st.spinner("Mando il video su TikTok..."):
                                _res2 = _tkpub2.pubblica(
                                    st.session_state["canzone_video"],
                                    _token2, _cap2, _priv2)
                            if _res2.get("ok"):
                                st.success("\u2705 " + _res2.get("messaggio",
                                                                   "Pubblicato!"))
                            else:
                                _m2 = str(_res2.get("messaggio", ""))
                                st.error(_m2)
                                if "unaudited" in _m2.lower():
                                    st.info("TikTok non ha ancora approvato "
                                            "la tua app per i video pubblici: "
                                            "per ora si pubblica come "
                                            "privato. Appena approva, "
                                            "ricarica la pagina e rifai.")
                else:
                    st.markdown(
                        '<div class="note">\U0001F517 Per <b>pubblicare con un '
                        'tocco</b> (senza aprire TikTok) collega il tuo '
                        'account: in fondo, in "Pubblica su TikTok", trovi '
                        '"Collega il tuo TikTok".</div>',
                        unsafe_allow_html=True)

# ==========================================================================
# PASSAGGIO 4 - PUBBLICA
# ==========================================================================

post = st.session_state["post"]
if post:
    html('<hr>')
    html(
        '<div class="step">PASSAGGIO 3</div><h3>\U0001F4E4 Prepara e pubblica</h3>')

    _rifl_post = post.get("riflessione") or st.session_state.get(
        "riflessione_giornaliera")
    if _rifl_post:
        html(
            '<div class="box box-ok"><b>\U0001F4DD La tua riflessione '
            '(dal post):</b><br><span style="font-size:1.02rem;">'
            f'«{esc(_rifl_post)}»</span></div>')

    html(
        f'<div class="box"><b>\U0001F3B5 Canzone scelta:</b> {esc(post["titolo"])}'
        f'<br><span class="note">Canale: {esc(post["canale"])}</span></div>')

    # ---- CAMBIARE / ANNULLARE LA CANZONE ----
    _c1, _c2 = st.columns(2)
    with _c1:
        if st.button("\U0001F504 Scegli un'altra canzone",
                     use_container_width=True, key="cambia_canzone"):
            st.session_state["post"] = None
            st.session_state["scelta"] = None
            st.rerun()
    with _c2:
        if st.button("\U0001F6D1 Annulla tutto (canzone e post)",
                     use_container_width=True, key="annulla_post"):
            st.session_state["post"] = None
            st.session_state["scelta"] = None
            st.session_state["risultati"] = []
            st.session_state["query_usate"] = []
            st.session_state["visti"] = []
            st.session_state["quante_mostrate"] = 0
            st.rerun()
    html(
        '<div class="note">Non ti piace? <b>Scegli un\'altra canzone</b> ti '
        'riporta alla lista: ne scegli un\'altra e prepari il post. '
        '<b>Annulla tutto</b> azzera la ricerca e cominci da capo.</div>')

    formato = st.selectbox("Come vuoi impostare il post?", list(FORMATI_POST),
                            index=list(FORMATI_POST).index(post["formato"])
                            if post["formato"] in FORMATI_POST else 0,
                            key="formato_post")
    hashtag = genera_hashtag(testo, poste_chiave := estrai_parole_chiave(testo, 3))
    # se l'IA ha gia' scritto la caption (riflessione ridotta), parte da quella
    if "caption" in st.session_state:
        caption = st.text_area("Caption (modificabile prima di copiare)",
                                height=170, key="caption")
    else:
        caption = st.text_area(
            "Caption (modificabile prima di copiare)",
            value=(post.get("caption")
                   or genera_caption(testo, formato, hashtag)),
            height=170, key="caption")
    if "hook" in st.session_state:
        hook = st.text_area("Testo da mettere a schermo (primi 3 secondi)",
                            height=70, key="hook")
    else:
        hook = st.text_area(
            "Testo da mettere a schermo (primi 3 secondi)",
            value=post.get("hook") or genera_hook(testo),
            height=70, key="hook")

    # ---- LO SCRIPT DA DIRE, SCRITTO DALL'IA ----
    if post.get("corpo_ia"):
        _n_r = len(post.get("corpo_ia", []))
        html(f'<div class="note" style="margin-top:10px;"><b>\U0001F3A4 Lo '
             f'script da dire ({_n_r} righe, scritte dall\'IA):</b></div>')
        for _riga in post.get("corpo_ia", []):
            html(f'<div class="note">&bull; {esc(_riga)}</div>')
        _c_r1, _c_r2 = st.columns(2)
        with _c_r1:
            blocco_copia("\n".join(post.get("corpo_ia", [])), "copia_corpo_post",
                         "\U0001F4CB Copia lo script da dire")
        with _c_r2:
            blocco_copia(_post_completo({
                "hook": hook,
                "corpo": post.get("corpo_ia", []),
                "caption": caption,
                "cta": post.get("cta_ia", ""),
                "momento": post.get("momento_ia", {}),
            }), "copia_tutto_post", "\U0001F4CB Copia tutto il post")

    # ---- L'IMMAGINE DEL POST (generata dall'AI) ----
    with st.expander("\U0001F5BC️ Genera l'immagine del post (AI)"):
        st.markdown(
            '<div class="note">L\'AI disegna <b>l\'immagine</b> del post: '
            'quella che sta dietro al tuo verso. Serve per il video (sfondo) '
            'e per un post "foto" con la musica come audio.</div>',
            unsafe_allow_html=True)
        _stile_img2 = st.selectbox(
            "Che feeling vuoi?",
            ["Caldo e speranza", "Sereno e contemplativo",
             "Drammatico e profondo", "Luminoso e gioioso",
             "Notte e silenzio"],
            key="stile_immagine_post")
        if st.button("\U0001F3A8 Genera l'immagine",
                     use_container_width=True, key="genera_immagine_post"):
            with st.spinner("\U0001F3A8 Sto disegnando l'immagine..."):
                _ris_img2 = genera_immagine(
                    versetto=(testo or "")[:300],
                    tema=", ".join((st.session_state["analisi"] or {}).get(
                        "temi", [])[:2]),
                    stile=_stile_img2,
                    chiave_gemini=_chiave_gemini_attiva())
            if _ris_img2.get("ok"):
                st.session_state["immagine_ai"] = _ris_img2["file"]
                st.session_state["immagine_ai_fonte"] = _ris_img2.get("fonte", "")
                st.success("\u2705 Immagine pronta!")
            else:
                st.error("Non sono riuscito a generarla: "
                         + str(_ris_img2.get("errore", ""))[:150])
    if st.session_state.get("immagine_ai"):
        with open(st.session_state["immagine_ai"], "rb") as _f:
            st.image(st.session_state["immagine_ai"], width=240)
            st.download_button(
                "\U0001F5BC️ Scarica l'immagine", data=_f.read(),
                file_name="cantico_immagine.png", mime="image/png",
                key="dl_immagine_post")

    # ---- Data e orario di pubblicazione ----
    html('<div class="note" style="margin-top:10px;"><b>\U0001F4C5 '
                'Quando lo pubblichi?</b></div>')

    # ---- IL MOMENTO CONSIGLIATO DALL'IA (precompila data e ora) ----
    _mom_post = (post.get("momento_ia") or {})
    if _mom_post.get("giorno"):
        html(
            f'<div class="box box-ok"><b>\U0001F4C5 Momento consigliato per '
            f'questo post:</b> {esc(_mom_post.get("giorno",""))} &mdash; '
            f'{esc(_mom_post.get("fascia",""))} '
            f'({esc(_mom_post.get("orario",""))})<br>'
            f'<span class="note">{esc(_mom_post.get("motivo",""))}</span>')
        if _mom_post.get("consiglio"):
            html(f'<div class="note"><b>Consiglio:</b> '
                 f'{esc(_mom_post.get("consiglio",""))}</div>')
        if st.button("\U0001F4C5 Metti questo momento",
                     use_container_width=True, key="usa_momento_ia"):
            st.session_state["_data_momento"] = _mom_post
            st.rerun()
    else:
        # nessun momento ancora: l'app lo calcola sul contenuto del post
        if st.button("\U0001F9E0 Consigliami il momento giusto",
                     use_container_width=True, key="chiedi_momento_ia",
                     help="L'IA guarda il tono del tuo post e ti dice il "
                          "giorno e l'ora migliori per pubblicarlo."):
            with st.spinner("\U0001F9E0 Calcolo il momento giusto..."):
                _mom = momento_migliore(
                    hook=hook, contenuto=caption,
                    tema=", ".join((st.session_state["analisi"] or {}).get(
                        "temi", [])[:2]),
                    riferimento=(st.session_state.get("riferimento") or {}).get(
                        "riferimento", ""),
                    chiave_gemini=_chiave_gemini_attiva(),
                    chiave_openai=st.session_state.get("chiave_ia", ""))
            if _mom.get("giorno"):
                st.session_state["post"]["momento_ia"] = _mom
                st.session_state["_data_momento"] = _mom
                st.rerun()
            else:
                st.info("Non riesco a calcolare il momento: riprova dopo.")

    # calcola la data del giorno consigliato (il prossimo di quel giorno)
    _data_ia = None
    _m = st.session_state.get("_data_momento") or {}
    if _m.get("giorno"):
        try:
            _idx = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì",
                    "sabato", "domenica"].index(_m["giorno"])
            _oggi = date.today()
            _delta = (_idx - _oggi.weekday()) % 7 or 7
            _data_ia = _oggi + timedelta(days=_delta)
        except Exception:
            _data_ia = None

    suggerimenti = suggerisci_orari(date.today() + timedelta(days=1))
    col_data, col_ora = st.columns(2)
    with col_data:
        data_pub = st.date_input(
            "Data di pubblicazione",
            value=(_data_ia or date.today() + timedelta(days=1)),
            key="data_pub")
    with col_ora:
        opzioni_orario = [s["orario"] for s in suggerisci_orari(data_pub)]
        _ora_ia = _m.get("orario", "")
        if _ora_ia and _ora_ia not in opzioni_orario:
            opzioni_orario.append(_ora_ia)
        ora_pub = st.selectbox("Orario consigliato", opzioni_orario,
                                index=(opzioni_orario.index(_ora_ia)
                                       if _ora_ia in opzioni_orario else 0),
                                key="ora_pub")
    motivo = next((s["motivo"] for s in suggerisci_orari(data_pub)
                   if s["orario"] == ora_pub), "")
    if _m.get("motivo") and ora_pub == _m.get("orario"):
        motivo = _m["motivo"]
    html(
        f'<div class="box box-ok">\U0001F4C5 <b>{giorno_settimana(data_pub)} '
        f'{data_pub.strftime("%d/%m/%Y")} alle {ora_pub}</b><br>'
        f'<span class="note">{esc(motivo)}</span></div>')

    html(
        '<div class="note" style="margin-bottom:4px;"><b>Hashtag suggeriti:</b></div>'
        + "".join(f'<span class="chip">{esc(h)}</span>' for h in hashtag))

    col_a, col_b = st.columns(2)
    with col_a:
        blocco_copia(caption, "copy_caption", "\U0001F4CB Copia Caption")
    with col_b:
        blocco_copia(" ".join(hashtag), "copy_hashtag", "\U0001F4CB Copia Hashtag")

    # ======================================================================
    # PUBBLICA SU TIKTOK (automatico, o la strada semplice in 2 gesti)
    # ======================================================================
    try:
        _tkpub = hotreload._modulo_fresco("tiktok_pubblica")
    except Exception:
        _tkpub = None

    html('<hr><div class="step">PUBBLICA</div>'
         "<h3>\U0001F4E4 Pubblica su TikTok</h3>")
    _errore_tk = None

    # ---- il video da pubblicare ----
    _video_gia = st.session_state.get("canzone_video") or ""
    _nome_video = ""
    if _video_gia and os.path.exists(_video_gia):
        _nome_video = os.path.basename(_video_gia)
    _file_up = None
    if not _nome_video:
        html(
            '<div class="note">L\'app ha gia\' la caption, il testo a schermo '
            'e l\'ora giusta. Per il <b>video</b> ci sono due strade:<br>'
            '<b>1) Canzone gia\' su YouTube</b>: il video lo fai <b>tu</b> '
            '(CapCut, Canva, o sul telefono: la tua voce o la musica + il '
            'testo a schermo). Poi o lo <b>carichi qui sopra</b> (l\'app lo '
            'tiene per l\'auto-pubblicazione) o lo scegli da TikTok Studio.'
            '<br><b>2) Vuoi che l\'app prepari tutto</b>: vai in "Crea una '
            'canzone ORIGINALE" -> "FAI TUTTO: parole + canzone + poster + video": '
            'l\'app scrive il testo, lo fa cantare e ti prepara il video '
            'verticale 9:16. Poi qui sotto compare "1) Scarica il video".'
            '</div>')
        _file_up = st.file_uploader("Il tuo video (mp4, verticale 9:16)",
                                    type=["mp4", "mov", "webm"],
                                    key="video_da_pubblicare")
        if _file_up is not None:
            _dest = os.path.join(tempfile.gettempdir(),
                                 "video_da_pubblicare" +
                                 os.path.splitext(_file_up.name)[1])
            with open(_dest, "wb") as _f:
                _f.write(_file_up.getvalue())
            _video_gia = _dest
            _nome_video = os.path.basename(_dest)
            st.session_state["canzone_video"] = _dest

    if _tkpub is None:
        st.info("Modulo di pubblicazione non disponibile: aggiorna l'app.")
    else:
        # le chiavi della developer app: dal server (Secrets) o dal browser
        # dell'utente (ognuno puo' usare la sua)
        def _tk_cookie(nome: str) -> str:
            """Legge un cookie (con ripiego: se il modulo e' vecchio, vuoto)."""
            try:
                return str(_tkpub._cookie(nome) or "").strip()
            except Exception:
                return ""

        _tk_utente = {
            "client_key": _tk_cookie("cantico_tk_key"),
            "client_secret": _tk_cookie("cantico_tk_secret"),
            "redirect_uri": _tk_cookie("cantico_tk_redirect"),
        }
        _tk_utente = {k: v for k, v in _tk_utente.items() if v}
    if _tkpub is None:
        pass
    elif not _tkpub.collegato(_tk_utente):
        # ---------- STRADA 1: la piu' semplice (funziona subito) ----------
        html(
            '<div class="box box-ok"><b>\u2705 Post pronto.</b> Ti manca solo '
            'un gesto: scarica il video e caricalo su TikTok Studio, dove la '
            'caption e\' <b>gia\' scritta</b>.<br>'
            '<b>1)</b> scarica il video &rarr; <b>2)</b> apri TikTok Studio '
            '(il pulsante qui sotto) &rarr; <b>3)</b> scegli il file e '
            'pubblica.</div>')
        _c_p1, _c_p2 = st.columns(2)
        with _c_p1:
            if _video_gia and os.path.exists(_video_gia):
                with open(_video_gia, "rb") as _f:
                    _dati = _f.read()
                st.download_button(
                    "\U0001F4BE 1) Scarica il video (.mp4)", data=_dati,
                    file_name="cantico_tiktok.mp4", mime="video/mp4",
                    use_container_width=True, key="dl_video_pubblica")
            else:
                st.info("Carica il video qui sopra (o fallo costruire "
                        "dall'app nella sezione 'Crea una canzone ORIGINALE').")
        with _c_p2:
            # un pulsante che COPIA la caption e POI apre TikTok Studio:
            # in Studio basta incollare (Ctrl+V) e pubblicare
            _url_studio = _tkpub.link_studio(caption)
            _cap_js = _js_string(caption)
            _url_js = _js_string(_url_studio)
            html(
                '<button id="cantico_studio" style="width:100%;min-height:50px;'
                'border:none;border-radius:14px;font-weight:700;font-size:1rem;'
                'color:#fff;cursor:pointer;'
                'background:linear-gradient(135deg,#4f46e5,#7c3aed);'
                'box-shadow:0 4px 14px rgba(79,70,229,.28)">'
                '\U0001F4E4 2) Apri TikTok Studio (testo gia\' pronto)</button>'
                '<script>(function(){'
                'try{ var b=document.getElementById("cantico_studio");'
                'if(!b || b.__pronto) return; b.__pronto = true;'
                'b.addEventListener("click", function(){'
                'var t = ' + _cap_js + ';'
                'try{ if(navigator.clipboard && navigator.clipboard.writeText){'
                'navigator.clipboard.writeText(t); } }catch(e){}'
                'window.open(' + _url_js + ',"_blank");'
                '}); }catch(e){}})();</script>',
                js=True)
            st.caption("Copia la caption e apre TikTok Studio: li' fai "
                       "Ctrl+V e pubblichi.")
        with st.expander("\u26A1 Volo pubblicare in automatico? (per chi puo')"):
            html(
                '<div class="note">TikTok permette di pubblicare in automatico '
                'solo a chi ha una <b>developer app</b> approvata. Con quella: '
                'ti colleghi una volta sola e l\'app <b>pubblica da sola</b> '
                'video, caption e privacy.<br>'
                'Serve una volta sola: crea l\'app su '
                '<a href="https://developers.tiktok.com" target="_blank">'
                'developers.tiktok.com</a>, attiva "Content Posting API" &rarr; '
                '"Direct Post", chiedi l\'approvazione dello scope '
                '<b>video.publish</b> e metti le chiavi nei Secrets di '
                'Streamlit Cloud:<br>'
                '<code>TIKTOK_CLIENT_KEY</code>, <code>TIKTOK_CLIENT_SECRET'
                '</code>, <code>TIKTOK_REDIRECT_URI</code>.<br>'
                'Finche\' non e\' pronto, la strada qui sopra funziona '
                'per sempre e ti costa 3 secondi.</div>',
                unsafe_allow_html=True)
            html(_tkpub.SCRIPT_CHIAVI_TIKTOK, js=True)
            with st.expander("Le chiavi della mia developer app"):
                st.text_input("Client Key", type="password",
                              key="tk_client_key", placeholder="aw...")
                st.text_input("Client Secret", type="password",
                              key="tk_client_secret", placeholder="...")
                st.text_input("Redirect URI", type="password",
                              key="tk_redirect_uri",
                              placeholder="https://la-tua-app.streamlit.app/")
                st.caption("Restano nel tuo browser: nessuno le vede. "
                           "Premi il pulsante qui sotto per salvarle.")
                if st.button("\U0001F4BE Salva le chiavi nel browser",
                             key="salva_chiavi_tk"):
                    st.rerun()
            if st.button("\U0001F50E Verifica la configurazione di TikTok",
                          use_container_width=True, key="verifica_tiktok_cfg"):
                _k = _tkpub.chiavi(_tk_utente)
                _mancano = [n for n, v in (("Client Key", _k.get("client_key")),
                                            ("Client Secret",
                                             _k.get("client_secret")),
                                            ("Redirect URI",
                                             _k.get("redirect_uri"))) if not v]
                if not _mancano:
                    st.success("\u2705 Tutto pronto! Comparirà il pulsante "
                               "\"Collega il tuo TikTok\".")
                else:
                    st.warning("Mancano: " + ", ".join(_mancano))
                    st.info("Apri l'expander qui sopra e incollale: restano "
                            "nel tuo browser.")
            with st.expander("\U0001F4D6 La guida passo passo (da tenere)"):
                html(
                    '<div class="note"><b>1)</b> Vai su '
                    '<a href="https://developers.tiktok.com" target="_blank">'
                    'developers.tiktok.com</a> e accedi col tuo TikTok<br>'
                    '<b>2)</b> "Create an app" &rarr; scegli <b>Web</b> (o '
                    'Other) e metti qualsiasi URL (es. '
                    'https://example.com)<br>'
                    '<b>3)</b> Nel pannello dell\'app attiva '
                    '<b>Content Posting API</b> &rarr; <b>Direct Post</b><br>'
                    '<b>4)</b> Chiedi l\'approvazione dello scope '
                    '<b>video.publish</b> (ci mette qualche giorno)<br>'
                    '<b>5)</b> Copia <b>Client Key</b> e <b>Client Secret</b><br>'
                    '<b>6)</b> Nei Secrets di Streamlit Cloud metti:<br>'
                    '<code>TIKTOK_CLIENT_KEY = "..."</code><br>'
                    '<code>TIKTOK_CLIENT_SECRET = "..."</code><br>'
                    '<code>TIKTOK_REDIRECT_URI = '
                    '"https://canzoni-pentecostali-enzo.streamlit.app/"</code>'
                    '<br>(il Redirect URI deve essere <b>esattamente</b> '
                    'l\'indirizzo della tua app)<br>'
                    '<b>7)</b> Salva, torna qui e premi "Collega il tuo '
                    'TikTok".</div>',
                    unsafe_allow_html=True)
    else:
        # ---------- STRADA 2: pubblicazione automatica ----------
        # il token vive nel browser: lo script lo rimette nel campo
        try:
            html(_tkpub.SCRIPT_LEGGI_TOKEN, js=True)
        except Exception:
            pass
        _campo_token = st.text_input(
            "Il tuo token TikTok (si ricorda da solo)",
            type="password", key="tiktok_token_campo")
        if _campo_token:
            st.session_state["tiktok_token"] = _campo_token.strip()
        _token = (st.session_state.get("tiktok_token") or "").strip()
        if not _token:
            html(
                '<div class="box"><b>Pubblicazione automatica disponibile.</b> '
                'Collega il tuo TikTok (una volta sola): si apre TikTok, '
                'autorizzi l\'app e torni qui.<br>'
                '<span class="note">Se TikTok ti dice che lo scope '
                '<b>video.publish</b> non e\' ancora approvato: vai su '
                '<a href="https://developers.tiktok.com/portal/apps" '
                'target="_blank">developers.tiktok.com</a> &rarr; la tua app '
                '&rarr; <b>Submit for review</b> (o "Scopes" &rarr; '
                'video.publish &rarr; Request) e aspetta l\'approvazione. '
                'Fino ad allora i video automatici restano <b>privati</b>: '
                'per pubblicare per davvero usa la strada qui sopra '
                '(3 secondi).</span></div>')
            if st.link_button("\U0001F517 Collega il tuo TikTok",
                              _tkpub.url_authorize("cantico", _tk_utente),
                              use_container_width=True, type="primary"):
                st.info("Autorizza l'app su TikTok: poi torna qui.")
        else:
            _info = _tkpub.creator_info(_token)
            if _info.get("errore"):
                st.warning("TikTok: " + str(_info["errore"])[:150])
            else:
                html(f'<div class="note box-ok">\u2705 Collegato come '
                     f'<b>{esc(_info.get("nickname") or _info.get("username"))}'
                     f'</b></div>')
            _opzioni = _info.get("privacy") or ["SELF_ONLY"]
            _privacy = st.selectbox(
                "Chi puo' vedere il video?",
                list(_opzioni),
                format_func=lambda x: _tkpub.PRIVACY.get(x, x),
                key="tiktok_privacy")
            if st.button("\U0001F4E4 Pubblica ora", type="primary",
                         use_container_width=True, key="pubblica_ora"):
                if not _video_gia or not os.path.exists(_video_gia):
                    st.warning("Prima carica il video \U0001F4D8")
                else:
                    with st.spinner("Mando il video su TikTok..."):
                        _res = _tkpub.pubblica(
                            _video_gia, _token, caption, _privacy)
                    if _res.get("ok"):
                        st.success("\u2705 " + _res.get("messaggio", "Pubblicato!"))
                    else:
                        _msg = str(_res.get("messaggio", "Pubblicazione fallita."))
                        st.error(_msg)
                        if ("scope" in _msg.lower()
                                or "unauthorized" in _msg.lower()
                                or "unaudited" in _msg.lower()):
                            html(
                                '<div class="box box-warn"><b>Motivo:</b> '
                                'TikTok non ha ancora approvato lo scope '
                                '<b>video.publish</b> per la tua app (o non ha '
                                'superato l\'audit).<br>Apri '
                                '<a href="https://developers.tiktok.com/portal/apps" '
                                'target="_blank">developers.tiktok.com</a> '
                                '&rarr; la tua app &rarr; <b>Submit for '
                                'review</b>.<br>Intanto pubblica con la strada '
                                'da 3 secondi qui sopra.</div>',
                                unsafe_allow_html=True)
            with st.expander("Scarica il video / apri TikTok Studio"):
                _c_p1, _c_p2 = st.columns(2)
                with _c_p1:
                    if _video_gia and os.path.exists(_video_gia):
                        with open(_video_gia, "rb") as _f:
                            _dati = _f.read()
                        st.download_button(
                            "\U0001F4BE Scarica il video (.mp4)", data=_dati,
                            file_name="cantico_tiktok.mp4", mime="video/mp4",
                            use_container_width=True, key="dl_video_auto")
                with _c_p2:
                    st.link_button("\U0001F4E4 Apri TikTok Studio",
                                   _tkpub.link_studio(caption),
                                   use_container_width=True)

    with st.expander("\U0001F3A7 Anteprima della canzone"):
        embed_youtube(post["video_id"])

    with st.expander("\U0001F4D7 Piano del video (come girarlo)"):
        html(
            f"""
            <div class="timeline">
            <b>0-3 secondi</b> &rarr; testo a schermo: <i>«{esc(hook)}»</i><br>
            <b>3-8 secondi</b> &rarr; inquadra il versetto / il cielo / un libro<br>
            <b>8-20 secondi</b> &rarr; parte la canzone: <i>{esc(post["titolo"])}</i><br>
            <b>20-25 secondi</b> &rarr; schermata finale con la domanda + CTA<br>
            <b>Durata totale</b> &rarr; {(st.session_state["analisi"] or {}).get("durata_video", "20-30 secondi")}<br>
            <b>Consiglio</b> &rarr; scegli la parte della canzone che ripete il titolo,
            cos\u00ec il suono su TikTok si riconosce subito.
            </div>
            """)

    with st.expander("\U0001F4F1 Come si pubblica dal telefono (5 passaggi)"):
        html(
            f"""
            <div class="timeline">
            1. Tocca <b>"Apri TikTok per pubblicare"</b> (si apre l'app o il sito)<br>
            2. Carica il tuo video (o registra nuovo)<br>
            3. Tocca <b>"Aggiungi suono"</b> e incolla il titolo copiato:
               <i>{esc(post["titolo"])}</i><br>
            4. Scegli l'audio e la parte giusta (quella che ripete il titolo)<br>
            5. Incolla la caption (copiata col pulsante qui sopra), aggiungi gli hashtag
               e <b>pubblica</b><br><br>
            <i>Nota: la pubblicazione automatica non è possibile per una web app
            gratuita, perché TikTok richiede l'approvazione delle API per gli
            sviluppatori. Con questa app prepari tutto in 10 secondi e pubblichi
            con 3 tocchi.</i>
            </div>
            """)

    contenuto = (
        f"CANZONE: {post['titolo']}\n"
        f"CANALE: {post['canale']}\n"
        f"PUBBLICAZIONE: {giorno_settimana(data_pub)} "
        f"{data_pub.strftime('%d/%m/%Y')} alle {ora_pub}\n\n"
        f"TESTO A SCHERMO:\n{hook}\n\n"
        f"CAPTION:\n{caption}\n\n"
        f"HASHTAG:\n{' '.join(hashtag)}\n\n"
        f"RICERCA AUDIO TIKTOK:\n{link_ricerca_audio(post['titolo'])}\n"
    )
    st.download_button(
        "\U0001F4E4 Scarica il pacchetto del post (.txt)",
        data=contenuto,
        file_name="pacchetto_post_tiktok.txt",
        mime="text/plain",
        use_container_width=True,
    )

    if st.button("\U0001F4BE Salva nell'archivio (resta qui nell'app)",
                 use_container_width=True):
        voce = {
            "testo": (testo or "").strip(),
            "canzone": post["titolo"],
            "video_id": post["video_id"],
            "canale": post["canale"],
            "hook": hook,
            "caption": caption,
            "hashtag": hashtag,
            "formato": formato,
            "data": data_pub.strftime("%d/%m/%Y"),
            "ora": ora_pub,
            "giorno": giorno_settimana(data_pub),
        }
        st.session_state["archivio"] = aggiungi_post(
            voce,
            _CHIAVE_ARCHIVIO,
            voci_correnti=st.session_state.get("archivio") or [])
        if st.session_state.get("codice_archivio"):
            st.success("\u2705 Post salvato nel tuo archivio privato.")
        else:
            st.warning("\u26A0\uFE0F Post salvato solo per questa sessione. "
                       "Metti un codice qui sotto nell'ARCHIVIO per ritrovarlo "
                       "anche dopo aver chiuso il browser.")

# ==========================================================================
# Informazioni: TikTok + come si usa + cronologia
# ==========================================================================

with st.expander("\U0001F517 Come funziona la ricerca su TikTok"):
    html(f'<div class="box box-warn">{esc(MESSAGGIO_TIKTOK)}</div>')
    html(
        '<div class="note">In più l\'app usa YouTube (ricerca pubblica, senza API '
        'a pagamento) per trovare i titoli reali delle canzoni pentecostali: sono '
        'gli stessi titoli che trovi nella libreria audio di TikTok.</div>')

with st.expander("\U0001F4D6 Come si usa l'app (guida rapida)"):
    html(
        """
        <div class="timeline">
        <b>1.</b> Incolla il versetto o la riflessione nel campo di testo.<br>
        <b>2.</b> (Opzionale) Tocca <b>"Correggi il testo"</b>: l'app segnala gli
        errori di ortografia/grammatica e te li corregge da sola.<br>
        <b>3.</b> Tocca <b>"Trova Canzone Adatta"</b>: l'app estrae 3 parole chiave,
        le unisce a "musica evangelica pentecostale lode" / "inno pentecostale"
        e cerca su YouTube.<br>
        <b>4.</b> Scorri i risultati: ogni canzone ha la spiegazione
        <b>"Perché questa canzone"</b> e i pulsanti <b>Copia Titolo</b> /
        <b>Cerca l'audio su TikTok</b>.<br>
        <b>4b.</b> <b>Nessuna ti convince?</b> Tocca <b>"Cerca meglio"</b>:
        l'app ti porta <b>altre 5 canzoni diverse</b>, sempre ordinate per
        adattamento al tuo versetto. Puoi ripeterlo quante volte vuoi.<br>
        <b>5.</b> Tocca <b>"Scegli questa canzone per il post"</b>: si apre il
        pacchetto di pubblicazione con caption, hashtag, testo a schermo e piano
        del video.<br>
        <b>5b.</b> Cambi idea? Nella sezione del post trovi
        <b>"Scegli un'altra canzone"</b> (torna alla lista) e
        <b>"Annulla tutto"</b> (azzera e ricomincia).<br>
        <b>6.</b> Copia caption e hashtag, apri TikTok e pubblica.<br><br>
        <i>Se il testo è un Salmo, l'app lo riconosce (anche con la numerazione
        Vulgate) e aggiunge la ricerca degli inni dedicati a quel Salmo.</i>
        </div>
        """)

cronologia = st.session_state["cronologia"]
if cronologia:
    with st.expander(f"\U0001F504 Cronologia ricerche ({len(cronologia)})"):
        for voce in cronologia:
            html(
                f'<div class="note"><b>{esc(voce["ora"])}</b> &mdash; {esc(voce["testo"])}'
                f'<br><i>parole chiave: {esc(voce["parole"])}</i></div>')

# ==========================================================================
# IL MIO ARCHIVIO
# ==========================================================================

archivio = st.session_state["archivio"] or []
_codice_attivo = st.session_state.get("codice_archivio", "")
html('<hr>')
html(
    '<div class="step">ARCHIVIO</div><h3>\U0001F5C2 Post pronti da pubblicare</h3>')

if _codice_attivo:
    html(
        '<div class="note box-ok">\U0001F510 <b>L\'archivio e\' privato.</b> '
        'Quello che cerchi resta solo per te: nessun altro vede i tuoi '
        'post, e tu non vedi quelli degli altri.</div>')
else:
    html(
        '<div class="note box-ok">\U0001F510 <b>L\'archivio e\' gi\' attivo '
        'per te.</b> L\'app ti ha riconosciuto dal browser: i tuoi post '
        'sono gi\' tuoi, <b>senza che tu debba creare o ricordare nessun '
        'codice</b>. Nessun altro li vede.</div>')

# campo codice qui (l'utente e' gia' in questa sezione: non deve
# andare a cercarlo da un'altra parte)
def _genera_codice() -> str:
    """Codice casuale leggibile (es. CANT-7K3M9P)."""
    import secrets
    import string
    alfabeto = string.ascii_uppercase + string.digits
    blocco = "".join(secrets.choice(alfabeto) for _ in range(6))
    return f"CANT-{blocco}"


with st.expander("Opzionale: ritrovare i tuoi post su un altro dispositivo"):
    html(
        '<div class="note">Non ti serve per usare l\'app: l\'archivio gi\' '
        'funziona. Ma se un giorno cambi telefono o computer, metti qui un '
        '<b>codice segreto</b> e ritrovi i tuoi post anche li.</div>')
    if st.button("\U0001F3B2 Genera un codice per me",
                 use_container_width=True, key="gen_codice"):
        st.session_state["input_codice_archivio2"] = _genera_codice()
        st.rerun()

    with st.form("form_codice_archivio", border=False):
        _cod_inserito = st.text_input(
            "Codice archivio (facoltativo)",
            value=_codice_attivo,
            type="password",
            placeholder="es. enzo2026",
            help="Solo tu devi saperlo: con questo codice ritrovi i tuoi "
                 "post su un altro dispositivo.",
            key="input_codice_archivio2",
        )
        _salva_codice = st.form_submit_button(
            "\U0001F510 Salva il codice" if not _codice_attivo
            else "\U0001F510 Cambia codice", use_container_width=True)
    if _salva_codice:
        st.session_state["codice_archivio"] = _cod_inserito
        st.session_state["archivio"] = carica_archivio(_cod_inserito)
        st.rerun()

if not archivio:
    html(
        '<div class="note">Qui trovi tutto quello che prepari: canzone, caption, '
        'hashtag e data di pubblicazione. Resta salvato anche se chiudi il browser.'
        '<br><br><i>(Nel passaggio 3, tocca "Salva nell\'archivio")</i></div>')
else:
    oggi = date.today()
    for voce in archivio:
        with st.container(border=True):
            try:
                data_voce = datetime.strptime(voce.get("data", ""), "%d/%m/%Y").date()
                scelta_data = f"{giorno_settimana(data_voce)} {data_voce.strftime('%d/%m/%Y')}"
                countdown = (data_voce - oggi).days
            except Exception:
                scelta_data = voce.get("data", "-")
                countdown = 0
            badge = ("\U0001F7E2 oggi" if countdown == 0 else
                     f"\U0001F552 tra {countdown} giorni" if countdown > 0 else
                     "\U0001F6AB passato")
            html(
                f'<div class="badge">{esc(badge)} &bull; {esc(scelta_data)} '
                f'alle {esc(voce.get("ora", ""))}</div>'
                f'<div class="card-title">\U0001F3B5 {esc(voce.get("canzone", ""))}</div>'
                f'<div class="card-meta">{esc(voce.get("testo", "")[:90])}</div>')
            with st.expander("Vedi tutto"):
                html(
                    f'<div class="box"><b>Testo a schermo:</b> {esc(voce.get("hook", ""))}'
                    f'<br><br><b>Caption:</b><br>{esc(voce.get("caption", ""))}'
                    f'<br><br><b>Hashtag:</b> {esc(" ".join(voce.get("hashtag", [])))}</div>')
            c1, c2, c3 = st.columns(3)
            with c1:
                st.download_button(
                    "\U0001F4E4 .txt",
                    data=(f"CANZONE: {voce.get('canzone','')}\n"
                          f"PUBBLICAZIONE: {voce.get('data','')} alle {voce.get('ora','')}\n\n"
                          f"TESTO A SCHERMO:\n{voce.get('hook','')}\n\n"
                          f"CAPTION:\n{voce.get('caption','')}\n\n"
                          f"HASHTAG:\n{' '.join(voce.get('hashtag', []))}\n"),
                    file_name=f"post_{voce.get('id', 'post')}.txt",
                    mime="text/plain",
                    key=f"dl_{voce.get('id','')}",
                    use_container_width=True,
                )
            with c2:
                if st.button("\U0001F504 Ricarica", key=f"reload_{voce.get('id','')}",
                             use_container_width=True):
                    st.session_state["post"] = {
                        "titolo": voce.get("canzone", ""),
                        "video_id": voce.get("video_id", ""),
                        "canale": voce.get("canale", ""),
                        "hashtag": voce.get("hashtag", []),
                        "formato": voce.get("formato", "Versetto + domanda"),
                        "caption": voce.get("caption", ""),
                        "hook": voce.get("hook", ""),
                    }
                    st.session_state["testo_input"] = voce.get("testo", "")
                    st.rerun()
            with c3:
                if st.button("\U0001F5D1 Elimina", key=f"del_{voce.get('id','')}",
                             use_container_width=True):
                    st.session_state["archivio"] = elimina_post(
                        voce.get("id", ""),
                        _CHIAVE_ARCHIVIO)
                    st.rerun()

# pulsante privacy: cancella tutto quello che ho salvato
with st.expander("🔒 Cancella i miei dati"):
    html('<div class="note">Cancella <b>tutti</b> i post che hai salvato '
         'nell\'archivio (anche il file sul server). Non si puo\' annullare.'
         '</div>')
    if st.button("\U0001F5D1 Cancella tutto il mio archivio",
                 use_container_width=True, key="cancella_mio_archivio"):
        cancella_archivio(_CHIAVE_ARCHIVIO)
        st.session_state["archivio"] = []
        st.session_state["codice_archivio"] = ""
        st.success("Archivio cancellato.")
        st.rerun()

html(
    f'<div class="note" style="text-align:center;margin-top:18px;">'
    f'Fatto per i creator cristiani \U0001F49F<br>'
    f'<span style="opacity:.6">versione {BUILD}</span><br>'
    f'<span style="opacity:.6">CANTICO &bull; creato da {esc(AUTORE_APP)}</span></div>')

# pulsante "ricarica" per prendere subito la versione piu' recente
if st.button("\U0001F504 Ricarica la versione piu' recente", use_container_width=True):
    # pulisco le cache (st.cache non esiste: uso cache_data / cache_resource)
    try:
        st.cache_data.clear()
    except Exception:
        pass
    try:
        st.cache_resource.clear()
    except Exception:
        pass
    st.query_params["v"] = BUILD.replace(" ", "-")
    st.rerun()    # ---- CERCA SU TIKTOK (il titolo da usare) ----
    _query_tiktok = " ".join(estrai_parole_chiave(testo or "", 3)).strip()         or (testo or "").strip()[:60]
    html('<hr>')
    html(
        '<div class="step">PASSAGGIO 2</div>'
        '<h3>\U0001F50D Il titolo da cercare su TikTok</h3>')
    html(
        '<div class="note box-ok"><b>Perche\' questo titolo?</b> L\'app lo '
        'ricava dall\'interpretazione del tuo versetto: sono le parole '
        'spirituali che parlano del cuore del passaggio. Su TikTok cerca '
        '<b>questo titolo</b> nella libreria audio e trovi il suono '
        'originale.</div>')
    html(
        f'<div class="box"><b>Titolo da cercare:</b> {esc(_query_tiktok)}</div>')
    blocco_copia(_query_tiktok, "copia_titolo_tiktok",
                 "\U0001F4CB Copia il titolo per TikTok")
    st.link_button(
        "\U0001F50A Cerca questo titolo su TikTok",
        f"https://www.tiktok.com/search?q={__import__('urllib.parse').parse.quote(_query_tiktok)}",
        use_container_width=True,
        type="primary")
    st.caption("Si apre la ricerca di TikTok: da li\' scegli il suono "
               "originale (non il video di un altro). Se TikTok ti manda "
               "alla home, accedi col tuo account e riprova il link (la "
               "ricerca resta impostata).")
    html(
        '<div class="note" style="margin-top:8px;">'
        '<b>Il percorso completo (5 secondi):</b><br>'
        '1) tocca "Copia il titolo per TikTok" (il titolo e\' negli appunti)<br>'
        '2) apri TikTok sul telefono -> tocca "+" (nuovo video)<br>'
        '3) "Aggiungi suono" -> incolla il titolo -> scegli il suono<br>'
        '4) registra il video con quel suono e pubblica.<br><br>'
        '<b>Se non vuoi cercare niente:</b> vai qui sotto in "Crea una '
        'canzone ORIGINALE" -> "FAI TUTTO": l\'app ti prepara tutto '
        '(parole, canzone cantata, poster, video 9:16) e tu pubblichi.</div>')

