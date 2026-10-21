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
from datetime import date, datetime, timedelta

import streamlit as st

# --- hot-reload dei moduli locali ------------------------------------------
# Streamlit riesegue solo app.py, ma i moduli importati restano in
# sys.modules: se cambio youtube_search.py, senza questo blocco continua a
# girare il codice VECCHIO (stesso problema su Streamlit Cloud).
import hotreload  # noqa: E402  (deve stare PRIMA delle import locali)

_RI_CARICATI = hotreload.ricarica()

from ai_client import (chiave_da_secrets, interpreta_con_ia, interpreta_gratis,
                       link_chatgpt)
from archivio import aggiungi_post, carica_archivio, elimina_post
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
    link_tiktok_upload,
    suggerisci_orari,
)
from tiktok_sounds import (
    MESSAGGIO_TIKTOK,
    cerca_suoni_tiktok,
    link_ricerca_audio,
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
    cerca_interpretazioni,
    costruisci_query,
    estrai_parole_chiave,
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

# "versione" = VERSION.txt (commit) + data del file piu' recente
# (cosi' si vede subito se l'app online gira il codice giusto)
BUILD = hotreload.versione()

st.set_page_config(
    page_title="CANTICO - Dalla Parola alla Lode",
    page_icon="🎵",
    layout="centered",
    initial_sidebar_state="collapsed",
)

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


def _esc_attr(testo: str) -> str:
    """Testo pronto per un attributo HTML (escape di &, <, >, ")."""
    return (testo.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


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
    """Cerca i versetti biblici piu' adatti a un pensiero."""
    return cerca_versetti(testo, n)


def _imposta_testo(testo: str) -> None:
    """Callback: mette il testo scelto nella casella di input e avvia la ricerca."""
    st.session_state["testo_input"] = testo
    st.session_state["correzione"] = None
    st.session_state["_cerca_subito"] = True


def esegui_ricerca(testo: str) -> None:
    """Cerca la canzone adatta al testo e aggiorna lo stato dell'app."""
    st.session_state.pop("riferimento_forzato", None)
    testo_pulito = (testo or "").strip()
    if not testo_pulito:
        st.warning("Incolla prima un versetto o una riflessione \U0001F4D8")
        return

    parole_chiave = estrai_parole_chiave(testo_pulito, max_parole=3)
    st.session_state["analisi"] = analizza_testo(testo_pulito, parole_chiave)
    stile_scelto = st.session_state.get("stile_lode", "Lodi pentecostali / ADI")
    query = costruisci_query(testo_pulito, stile_scelto)
    st.session_state["query_usate"] = query
    _rif = _riferimento_breve(_riferimento_corrente())

    with st.spinner("\U0001F50D Sto cercando le canzoni piu' adatte..."):
        try:
            risultati = ricerca_cached(tuple(query), 5, tuple(parole_chiave),
                                       riferimento=_rif)
        except ErroreRicerca as exc:
            st.error(f"\u26A0\uFE0F {exc}")
            risultati = []
        except Exception as exc:
            st.error(f"\u26A0\uFE0F Errore durante la ricerca: {exc}")
            risultati = []

    st.session_state["risultati"] = risultati
    st.session_state["scelta"] = None
    st.session_state["suoni_tiktok"] = []
    # video gia' mostrati: "cerca meglio" deve dare canzoni NUOVE
    st.session_state["visti"] = [r.video_id for r in risultati]
    st.session_state["quante_mostrate"] = len(risultati)
    st.session_state["cronologia"].insert(
        0,
        {
            "testo": testo_pulito[:120],
            "parole": ", ".join(parole_chiave) if parole_chiave else "-",
            "ora": datetime.now().strftime("%d/%m %H:%M"),
        },
    )
    st.session_state["cronologia"] = st.session_state["cronologia"][:8]



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

    # --- FASE 1: le interpretazioni (esposizioni/studi evangelici) ---
    interpretazioni = cerca_interpretazioni(
        riferimento["libro"], riferimento["capitolo"], riferimento["versetto"],
        riferimento["riferimento"], testo_intero, 8)

    # la spiegazione scritta: trascrizione di una predicazione che parla
    # DAVVERO del versetto (controllo di pertinenza sulle parole chiave)
    trascrizione = None
    parole_verso = [p.lower() for p in
                    estrai_parole_chiave(testo_intero, 8)]
    for r in interpretazioni[:8]:
        t = estrai_spiegazione(r.video_id)
        if not t or len(t["testo"]) < 250:
            continue
        basso = t["testo"].lower()
        # 1) deve citare il NUMERO del nostro versetto
        _num = str(riferimento.get("versetto") or "")
        _cita_numero = True
        if _num:
            _cita_numero = bool(re.search(
                r"(?:v(?:ersetto|\.|°)?\s*|,\s*|^)\b" + re.escape(_num) + r"\b",
                basso))
        # 2) deve contenere le parole DISTINTE del nostro versetto
        _confronti = [p for p in parole_verso if len(p) > 3]
        _presenti = [p for p in _confronti if p in basso]
        _rapporto = (len(_presenti) / len(_confronti)) if _confronti else 0
        if _cita_numero and _rapporto >= 0.34:
            trascrizione = t["testo"]
            st.session_state["interp_pertinente"] = r.titolo
            break

    versetto["trascrizione"] = trascrizione
    analisi = st.session_state.get("analisi") or {}
    temi = analisi.get("temi") or ["Salvezza"]
    # se l'utente ha scelto di studiare SOLO un versetto, l'interpretazione
    # non deve citare i versetti vicini (scope = solo il versetto richiesto)
    _solo_versetto = bool(riferimento.get("versetto")) and not \
        riferimento.get("versetto_fine")
    interpretazione = interpretazione_dotrinale(
        versetto, temi[0], estrai_parole_chiave(testo_intero, 4),
        includi_contesto=not _solo_versetto)

    # --- FASE 2: query musicale forzata ---
    parole_spirituali = interpretazione["parole_chiave"][:3]
    if not parole_spirituali:
        parole_spirituali = ["fede", "lode", "consolazione"]
    rif_breve = _riferimento_breve(riferimento)
    query_stretta = (f"{rif_breve} {' '.join(parole_spirituali)} "
                     f"{FILTRO_PENTECOSTALE} {KEYWORD_NEGATIVE}")
    query_larga = (f"{' '.join(parole_spirituali)} inno pentecostale lode ADI "
                   f"{FILTRO_PENTECOSTALE} {KEYWORD_NEGATIVE}")
    query = [query_stretta, query_larga]
    try:
        risultati = ricerca_cached(tuple(query), 5, tuple(parole_spirituali),
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
    }
    st.session_state["risultati"] = risultati
    st.session_state["query_usate"] = query
    st.session_state["scelta"] = None
    st.session_state["visti"] = [r.video_id for r in risultati]
    st.session_state["quante_mostrate"] = len(risultati)
    st.session_state["studio_parole"] = list(parole_spirituali)


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
):
    if chiave not in st.session_state:
        st.session_state[chiave] = valore

if st.session_state["archivio"] is None:
    st.session_state["archivio"] = carica_archivio(
        st.session_state.get("codice_archivio", ""))



# --------------------------------------------------------------------------
# ACCESSO: password + pagina di benvenuto
# --------------------------------------------------------------------------

def _sha(testo: str) -> str:
    return hashlib.sha256((testo or "").encode("utf-8")).hexdigest()


def _password_attesa() -> str:
    """Legge l'hash della password dalle secrets (Cloud), dall'ambiente o
    dal file locale .streamlit/secrets.toml (mai committato)."""
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
    return ""


def richiedi_accesso() -> None:
    """Mostra la pagina di benvenuto e chiede la password.
    Se non c'e' password configurata, l'app resta aperta."""
    if st.session_state.get("accesso_ok"):
        return

    attesa = _password_attesa()
    if not attesa:
        st.session_state["accesso_ok"] = True
        return

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
# Sidebar: interpretazione con IA (facoltativa) + spiegazione
with st.sidebar:
    st.markdown("### \U0001F9E0 Interpretazione con IA")
    st.markdown(
        "<div class=\"note\">L'interpretazione dottrinale puo' arrivare da tre "
        "luoghi:<br>"
        "<b>1)</b> dalle <b>predicazioni reali</b> che l'app trova su YouTube "
        "(funziona senza account)<br>"
        "<b>2)</b> da <b>ChatGPT</b> con la tua chiave API<br>"
        "<b>3)</b> dall'<b>IA che hai sul telefono</b>: l'app ti copia il "
        "prompt gia' pronto e tu lo incolli qui<br><br>"
        "<b>Le canzoni le cerca sempre l'app</b> (brani reali, filtro "
        "pentecostale): ChatGPT non consiglia mai titoli di canzoni.</div>",
        unsafe_allow_html=True,
    )
    _chiave_ia = st.text_input(
        "Chiave API OpenAI (opzionale)",
        value=chiave_da_secrets(),
        type="password",
        help="Lasciala vuota se preferisci le predicazioni reali o l'IA del "
             "telefono. Va in .streamlit/secrets.toml per non riscriverla.",
        key="chiave_ia",
    )
    html(
        "<div class=\"note\">La chiave resta nel server di Streamlit. "
        "Con la chiave l'app chiama l'IA solo quando lo chiedi tu.</div>")

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
tab_verso, tab_biblia = st.tabs([
    "\U0001F3A5 Versetto -> canzone",
    "\U0001F4D6 Cerca in tutta la Bibbia",
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

    if st.button("\U0001F50E Trova Canzone Adatta", type="primary",
                  use_container_width=True):
        esegui_ricerca(testo)

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

    if salmo:
        if st.button("\U0001F4D6 Aggiungi anche gli inni sul Salmo", use_container_width=True):
            query = costruisci_query(testo, stile_scelto)
            query += query_per_salmo(salmo)
            query += query_per_salmo(salmo)
            st.session_state["query_usate"] = query
            with st.spinner("\U0001F50D Cerco gli inni dedicati a questo Salmo..."):
                try:
                    risultati = ricerca_cached(
                        tuple(query), 5, tuple(estrai_parole_chiave(testo, 3)),
                        riferimento=_riferimento_breve(_riferimento_corrente()))
                except Exception as exc:
                    st.error(f"\u26A0\uFE0F {exc}")
                    risultati = []
            st.session_state["risultati"] = risultati
            st.session_state["scelta"] = None
            st.session_state["visti"] = [r.video_id for r in risultati]
            st.session_state["quante_mostrate"] = len(risultati)
            st.rerun()

# --------------------------------------------------------------------------
# IL VERSETTO ESATTO indicato dall'utente (Fase 1 -> Fase 2)
# --------------------------------------------------------------------------

riferimento_verso = (st.session_state.get("riferimento_forzato")
                      or rileva_riferimento(testo or ""))
studio = st.session_state.get("versetto_studio") or {}

if riferimento_verso and not studio.get("errore"):
    versetto_esatto = studio.get("versetto") or trova_versetto(
        riferimento_verso["libro"], riferimento_verso["capitolo"],
        riferimento_verso["versetto"] or 1,
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
                f'<div class="note">Testo integrale dalla {esc(NOME_TRADUZIONE)} '
                '(66 libri = canon protestante evangelico).</div>')
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
                    _rif = rileva_riferimento(
                        f"{riferimento_verso['libro']} {_cap_n} {_txt}")
                    if _rif and _rif.get("versetto"):
                        st.session_state["riferimento_forzato"] = _rif
                        st.rerun()
                    else:
                        st.warning("Scrivi l'intervallo, es. 6-10")
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
        f'<div class="box"><b>{esc(interp.get("fonte", ""))}</b>'
        f' <span class="note">({totale:,} caratteri totali)</span><br>'
        f'{esc(testo_interp)}</div>')

    # COPIA l'interpretazione (sempre) + SCARICALA
    _nome_file = (f"interpretazione_{v.get('riferimento', 'versetto')}"
                  .replace(" ", "_").replace(",", "-").replace(":", "-"))
    col_i1, col_i2 = st.columns(2)
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
    parole = interp.get("parole_chiave", [])[:3]
    if parole:
        html(
            '<div class="note" style="margin-top:6px;">'
            '<b>Le 3 parole chiave spirituali (usate nella ricerca musicale):</b></div>'
            + "".join(f'<span class="chip">{esc(p)}</span>' for p in parole))

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
        if st.button("\U0001F9E0 Interpreta con IA gratuita",
                     key="ia_gratis", use_container_width=True,
                     help="L'app scrive l'interpretazione con un'IA gratuita "
                          "che non richiede nessuna chiave. Ci mette 10-30 "
                          "secondi. Parti sempre dal testo del TUO versetto."):
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
                        "(IA gratuita, 10-30 secondi)..."):
            _ris = interpreta_gratis(_prompt_attuale)
        if _ris.get("errore"):
            st.warning(f"IA gratuita non disponibile: {_ris['errore']}")
            st.info("Nessun problema: l'app usa comunque lo studio del versetto "
                    "e le predicazioni reali che ha trovato su YouTube.")
        elif _ris.get("testo"):
            from studio_biblico import estrai_parole_chiave_spirituali
            st.session_state["versetto_studio"]["interpretazione"] = {
                "testo": _ris["testo"],
                "parole_chiave": estrai_parole_chiave_spirituali(_ris["testo"])[:3],
                "fonte": _ris.get("fonte", "IA gratuita"),
                "riferimento": studio.get("riferimento", {}).get("riferimento", ""),
            }
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


# --------------------------------------------------------------------------
# I versetti biblici trovati (dal pulsante "Trova il testo adatto")
# --------------------------------------------------------------------------

versetti = st.session_state.get("versetti") or []
if versetti:
    html(
        '<div class="step">Il testo biblico</div>'
        '<h3>\U0001F4D6 Versetti che parlano al tuo pensiero</h3>'
        f'<div class="note">Testo di riferimento: {esc(NOME_TRADUZIONE)}. '
        'Scegli il versetto che ti risuona: l\'app lo mette nella casella e cerca '
        'subito la canzone.</div>')
    for i, v in enumerate(versetti, start=1):
        with st.container(border=True):
            chip = "".join(f'<span class="chip">{esc(t)}</span>' for t in v["temi"])
            html(
                f'<div class="badge">#{i}</div>'
                f'<div class="card-title">{esc(v["riferimento"])}</div>'
                f'<div class="card-meta" style="font-size:.92rem;opacity:.85;">'
                f'«{esc(v["testo"])}»</div>{chip}')
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

# PASSAGGIO 2/3 - CERCA e SCEGLI
# ==========================================================================

risultati = st.session_state["risultati"]
query_usate = st.session_state["query_usate"]

if risultati:
    html('<hr>')
    html(
        '<div class="step">PASSAGGIO 2</div>'
        f'<h3>\U0001F3A4 {len(risultati)} canzoni trovate</h3>')
    html(
        '<div class="note">Copia il titolo e cercalo nella libreria audio di TikTok, '
        'oppure ascolta l\'anteprima qui sotto.</div>')

    # ---- CERCA MEGLIO / ALTRE CANZONI ----
    _visti = st.session_state.get("visti") or []
    _quante = st.session_state.get("quante_mostrate", len(risultati))
    html(
        '<div class="note" style="margin-top:8px;">'
        '<b>Nessuna di queste ti convince?</b> Tocca "Cerca meglio": '
        'l\'app ti porta <b>altre canzoni diverse</b>, ordinate sempre per '
        'adattamento al tuo versetto.</div>')
    _c1, _c2 = st.columns(2)
    with _c1:
        if st.button("\U0001F504 Cerca meglio (altre 5)",
                     use_container_width=True, key="cerca_meglio"):
            _query = st.session_state.get("query_usate") or []
            _kw = st.session_state.get("studio_parole") or \
                estrai_parole_chiave(testo or "", 3)
            _rif = _riferimento_breve(_riferimento_corrente())
            with st.spinner("\U0001F50D Cerco canzoni diverse e piu' adatte..."):
                try:
                    _nuovi = ricerca_cached(
                        tuple(_query), 5, tuple(_kw), DURATA_MAX_SEC,
                        escludi=tuple(_visti), riferimento=_rif)
                except Exception:
                    _nuovi = []
            if _nuovi:
                st.session_state["risultati"] = _nuovi
                st.session_state["visti"] = list(_visti) + \
                    [r.video_id for r in _nuovi]
                st.session_state["quante_mostrate"] = _quante + len(_nuovi)
                st.rerun()
            else:
                st.info("Non trovo altre canzoni diverse per questo versetto. "
                        "Prova a scrivere il testo in un altro modo.")
    with _c2:
        if st.button("\U0001F3A8 Cambia stile / parole chiave",
                     use_container_width=True, key="cambia_stile"):
            st.session_state["_apri_stile"] = True
            st.info("Sposta il campo 'Stile della lode cercata' in alto e "
                    "tocca di nuovo 'Trova Canzone Adatta': la ricerca "
                    "partira' con parole diverse.")
    html(
        '<div class="note">Finora mostrate: <b>'
        f'{st.session_state.get("quante_mostrate", len(risultati))}</b> canzoni '
        '(tutte diverse fra loro).</div>')

    parole_chiave = estrai_parole_chiave(testo or "", max_parole=3)
    temi = (st.session_state["analisi"] or {}).get("temi", [])

    for i, r in enumerate(risultati, start=1):
        with st.container(border=True):
            html(
                f"""
                <div style="display:flex;gap:12px;align-items:flex-start;">
                  <img class="thumb" src="{r.url_miniature}" alt="" loading="lazy">
                  <div style="flex:1;min-width:0;">
                    <div class="badge">#{i}</div>
                    <div class="card-title">{esc(r.titolo)}</div>
                    <div class="card-meta">{esc(r.canale)}"""
                + (f" &bull; {esc(r.durata)}" if r.durata else "")
                + "</div></div></div>")

            motivi = spiega_canzone(r.titolo, r.canale, r.durata, r.secondi,
                                    parole_chiave, temi)
            with st.expander("Perch\u00e9 questa canzone"):
                for motivo in motivi:
                    html(f'<div class="note">&bull; {esc(motivo)}</div>')

            col_a, col_b = st.columns([1, 1])
            with col_a:
                blocco_copia(r.titolo, f"copia{i}")
            with col_b:
                st.link_button("\U0001F3A7 Ascolta", r.url, use_container_width=True)

            st.link_button(
                "\U0001F50D Verifica l'audio su TikTok",
                link_ricerca_audio(r.titolo),
                use_container_width=True,
                help="Apre la ricerca dei suoni di TikTok con questo titolo: "
                     "vedi subito se l'audio e' disponibile per i tuoi video.",
            )
            if st.button(f"\u2B50 Scegli questa canzone per il post", key=f"scelta{i}",
                         use_container_width=True):
                st.session_state["scelta"] = i - 1
                hashtag = genera_hashtag(testo, parole_chiave)
                formato = (st.session_state["analisi"] or {}).get(
                    "formato_post", "Versetto + domanda")
                st.session_state["post"] = {
                    "titolo": r.titolo,
                    "video_id": r.video_id,
                    "canale": r.canale,
                    "hashtag": hashtag,
                    "formato": formato,
                    "caption": genera_caption(testo, formato, hashtag),
                    "hook": genera_hook(testo),
                }
                st.rerun()

    if query_usate:
        with st.expander("Query di ricerca utilizzate"):
            html(
                '<div class="box">'
                + "<br>".join(f"<b>{i+1}.</b> {esc(q)}" for i, q in enumerate(query_usate))
                + "</div>")

# ==========================================================================
# PASSAGGIO 4 - PUBBLICA
# ==========================================================================

post = st.session_state["post"]
if post:
    html('<hr>')
    html(
        '<div class="step">PASSAGGIO 3</div><h3>\U0001F4E4 Prepara e pubblica</h3>')

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
    caption = st.text_area("Caption (modificabile prima di copiare)",
                            value=genera_caption(testo, formato, hashtag),
                            height=170, key="caption")
    hook = st.text_area("Testo da mettere a schermo (primi 3 secondi)",
                        value=genera_hook(testo), height=70, key="hook")

    # ---- Data e orario di pubblicazione ----
    html('<div class="note" style="margin-top:10px;"><b>\U0001F4C5 '
                'Quando lo pubblichi?</b></div>')
    suggerimenti = suggerisci_orari(date.today() + timedelta(days=1))
    col_data, col_ora = st.columns(2)
    with col_data:
        data_pub = st.date_input("Data di pubblicazione",
                                  value=date.today() + timedelta(days=1),
                                  key="data_pub")
    with col_ora:
        opzioni_orario = [s["orario"] for s in suggerisci_orari(data_pub)]
        ora_pub = st.selectbox("Orario consigliato", opzioni_orario,
                                key="ora_pub")
    motivo = next((s["motivo"] for s in suggerisci_orari(data_pub)
                   if s["orario"] == ora_pub), "")
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

    st.link_button(
        "\U0001F4E4 Apri TikTok per pubblicare",
        link_tiktok_upload(caption),
        use_container_width=True,
        type="primary",
    )

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
            st.session_state.get("codice_archivio", ""),
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
        '<div class="note box-warn">\U0001F510 <b>L\'archivio e\' privato.</b> '
        'Quello che cerchi resta solo per te. Per ritrovare i tuoi post '
        'anche dopo aver chiuso il browser, metti un <b>codice</b> qui sotto.'
        '</div>')
    html(
        '<div class="note">\U0001F4DD <b>Come si usa il codice</b><br>'
        'Ogni persona che usa l\'app sceglie <b>il proprio</b> codice: '
        'basta che ognuno se lo ricordi (o se lo mandi su WhatsApp).<br>'
        'Nessuno deve sapere il codice degli altri: ognuno vede solo i '
        'suoi post. Se non vuoi complicarti, lascia pure il codice vuoto: '
        'l\'archivio funziona lo stesso, ma vale solo finche\' non chiudi '
        'il browser.</div>')

# campo codice qui (l'utente e' gia' in questa sezione: non deve
# andare a cercarlo da un'altra parte)
def _genera_codice() -> str:
    """Codice casuale leggibile (es. CANT-7K3M9P)."""
    import secrets
    import string
    alfabeto = string.ascii_uppercase + string.digits
    blocco = "".join(secrets.choice(alfabeto) for _ in range(6))
    return f"CANT-{blocco}"


if st.button("\U0001F3B2 Genera un codice per me", use_container_width=True):
    st.session_state["input_codice_archivio2"] = _genera_codice()
    st.rerun()

with st.form("form_codice_archivio", border=False):
    _cod_inserito = st.text_input(
        "Codice archivio (per ritrovare i tuoi post)",
        value=_codice_attivo,
        type="password",
        placeholder="es. enzo2026",
        help="Scegli un codice che solo tu conosci (o usa il pulsante "
             "'Genera un codice per me'). Serve per ritrovare i tuoi post "
             "dopo aver chiuso il browser.",
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
                        st.session_state.get("codice_archivio", ""))
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
    st.rerun()
