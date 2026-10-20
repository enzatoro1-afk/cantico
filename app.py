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

import html as html_mod
import json
from datetime import date, datetime, timedelta

import streamlit as st
import streamlit.components.v1 as components

from archivio import aggiungi_post, carica_archivio, elimina_post
from bible_search import NOME_TRADUZIONE, cerca_versetti
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
from studio_biblico import genera_passi, query_studio, rileva_riferimento
from text_tools import (
    analizza_testo,
    correggi_testo,
    query_per_salmo,
    spiega_canzone,
)
from youtube_search import (
    ErroreRicerca,
    STILI,
    costruisci_query,
    estrai_parole_chiave,
    ricerca_multipla,
)

# --------------------------------------------------------------------------
# Configurazione pagina
# --------------------------------------------------------------------------

st.set_page_config(
    page_title="Canzoni Pentecostali per TikTok",
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
st.markdown(CSS, unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Helper
# --------------------------------------------------------------------------

def esc(testo: str) -> str:
    return html_mod.escape(testo or "", quote=True)


def _js_string(testo: str) -> str:
    return json.dumps(testo, ensure_ascii=False).replace("</", "<\\/")


TEMPLATE_COPIA = """
<div style="display:flex;align-items:center;gap:8px;width:100%;">
  <button id="__ID__" style="width:100%;min-height:48px;border:none;border-radius:14px;
    background:linear-gradient(135deg,#4f46e5,#7c3aed);color:#fff;font-weight:700;font-size:.95rem;
    cursor:pointer;font-family:'Inter',system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
    box-shadow:0 4px 14px rgba(79,70,229,.28);">
    \U0001F4CB Copia Titolo
  </button>
  <span id="__ID__ok" style="display:none;font-weight:700;color:#16a34a;font-size:.85rem;white-space:nowrap;">\u2713 Copiato!</span>
</div>
<script>
(function(){
  var btn = document.getElementById("__ID__");
  var ok  = document.getElementById("__ID__ok");
  var txt = __TESTO__;
  function feedback(){
    ok.style.display = "inline-block";
    btn.textContent = "\u2705 Copiato!";
    setTimeout(function(){
      ok.style.display = "none";
      btn.textContent = "\U0001F4CB Copia Titolo";
    }, 1900);
  }
  function fallback(){
    try{
      var ta = document.createElement("textarea");
      ta.value = txt; ta.setAttribute("readonly","");
      ta.style.position = "fixed"; ta.style.top = "-1000px"; ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.focus(); ta.select(); ta.setSelectionRange(0, ta.value.length);
      var done = document.execCommand("copy");
      document.body.removeChild(ta);
      if (done) feedback();
    } catch(e){}
  }
  btn.addEventListener("click", function(){
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(txt).then(feedback).catch(fallback);
    } else { fallback(); }
  });
})();
</script>
"""


def blocco_copia(testo: str, chiave: str, etichetta: str = "\U0001F4CB Copia Titolo") -> None:
    """Pulsante 'Copia' con fallback per browser senza Clipboard API."""
    html = (
        TEMPLATE_COPIA
        .replace("__ID__", chiave)
        .replace("__TESTO__", _js_string(testo))
        .replace("\U0001F4CB Copia Titolo", etichetta)
    )
    render_html(html, height=54)


def embed_youtube(video_id: str) -> None:
    """Player YouTube incorporato (anteprima audio dal telefono)."""
    render_html(
        f"""
        <div style="width:100%;aspect-ratio:16/9;border-radius:14px;overflow:hidden;
                    box-shadow:0 4px 14px rgba(15,23,42,.15);">
          <iframe src="https://www.youtube.com/embed/{video_id}"
                  style="width:100%;height:100%;border:0;" allowfullscreen
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media"></iframe>
        </div>
        """,
        height=260,
    )


def render_html(html: str, height: int) -> None:
    """
    Mostra HTML con JavaScript, usando l'API piu' recente di Streamlit.

    - Streamlit >= 1.6x : st.iframe (accetta HTML ed esegue il JavaScript)
    - versioni precedenti: st.components.v1.html (deprecata, ma funzionante)
    """
    if hasattr(st, "iframe"):
        st.iframe(html, height=height)
    else:  # pragma: no cover - compatibilita' con Streamlit < 1.50
        components.html(html, height=height)


@st.cache_data(ttl=1800, show_spinner=False)
def ricerca_cached(query_list: tuple[str, ...], n: int,
                   parole_chiave: tuple[str, ...]) -> list:
    return ricerca_multipla(list(query_list), max_risultati=n,
                            parole_chiave=list(parole_chiave))


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
    testo_pulito = (testo or "").strip()
    if not testo_pulito:
        st.warning("Incolla prima un versetto o una riflessione \U0001F4D8")
        return

    parole_chiave = estrai_parole_chiave(testo_pulito, max_parole=3)
    st.session_state["analisi"] = analizza_testo(testo_pulito, parole_chiave)
    query = costruisci_query(parole_chiave, "Lodi pentecostali / ADI")
    st.session_state["query_usate"] = query

    with st.spinner("\U0001F50D Sto cercando le canzoni piu' adatte..."):
        try:
            risultati = ricerca_cached(tuple(query), 5, tuple(parole_chiave))
        except ErroreRicerca as exc:
            st.error(f"\u26A0\uFE0F {exc}")
            risultati = []
        except Exception as exc:
            st.error(f"\u26A0\uFE0F Errore durante la ricerca: {exc}")
            risultati = []

    st.session_state["risultati"] = risultati
    st.session_state["scelta"] = None
    st.session_state["suoni_tiktok"] = []
    st.session_state["cronologia"].insert(
        0,
        {
            "testo": testo_pulito[:120],
            "parole": ", ".join(parole_chiave) if parole_chiave else "-",
            "ora": datetime.now().strftime("%d/%m %H:%M"),
        },
    )
    st.session_state["cronologia"] = st.session_state["cronologia"][:8]


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
    ("studio_risultati", []),
    ("riferimento", None),
    ("versetti", []),
    ("_cerca_subito", False),
):
    if chiave not in st.session_state:
        st.session_state[chiave] = valore

if st.session_state["archivio"] is None:
    st.session_state["archivio"] = carica_archivio()


# --------------------------------------------------------------------------
# Intestazione
# --------------------------------------------------------------------------

st.markdown(
    """
    <div class="hero">
      <h1>\U0001F3B5 Assistente Canzoni Pentecostali</h1>
      <p>Scrivi il tuo versetto: l'app cerca la canzone evangelica giusta,
         ti spiega perché è adatta e prepara il post per TikTok.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ==========================================================================
# PASSAGGIO 1 - SCRIVI (correzione + analisi)
# ==========================================================================

st.markdown('<div class="step">PASSAGGIO 1</div><h3>\U0001F4DD Scrivi il tuo testo</h3>',
            unsafe_allow_html=True)

# Se c'è una correzione in attesa, il pannello sta PRIMA della text area
# (così il bottone "Applica" può aggiornare il campo senza errori di stato).
correzione = st.session_state["correzione"]
if correzione and correzione.get("problemi"):
    st.markdown(
        f'<div class="box box-ok">'
        f'<b>Testo corretto</b><br>{esc(correzione["testo"])}</div>',
        unsafe_allow_html=True,
    )
    with st.expander(f"Correzioni trovate ({len(correzione['problemi'])})", expanded=True):
        for p in correzione["problemi"]:
            st.markdown(
                f'<div class="note">\u2022 <b>{esc(p.get("breve") or p.get("messaggio", ""))}</b>'
                f' &mdash; <i>{esc(p.get("evidenzia", ""))}</i>'
                f'{" \u2192 " + esc(", ".join(p.get("sostituzioni", [])[:3])) if p.get("sostituzioni") else ""}'
                f'</div>',
                unsafe_allow_html=True,
            )
    if st.button("\u2705 Applica il testo corretto", use_container_width=True):
        st.session_state["testo_input"] = correzione["testo"]
        st.session_state["correzione"] = None
        st.rerun()
elif correzione:
    st.info("\u2705 Il tuo testo è già corretto: nessun errore rilevato.")

testo = st.text_area(
    "Versetto biblico o riflessione evangelica",
    placeholder=(
        "Es. «Il Signore è il mio pastore: nulla mi mancherà.»\n"
        "Oppure: «Dio, per il tuo amore io Ti ringrazio»"
    ),
    key="testo_input",
    height=170,
    max_chars=2000,
    label_visibility="collapsed",
)

if testo and len(testo) > 1900:
    st.markdown('<div class="note">Testo troncato a 2000 caratteri '
                '(per non rallentare la ricerca).</div>', unsafe_allow_html=True)

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
    st.markdown(
        f'<div class="box"><b>\U0001F9EA Analisi del testo</b><br>'
        f'<b>Temi:</b> {temi}<br>'
        f'<b>Tono:</b> {esc(analisi["tono"])}<br>'
        f'<b>Durata video consigliata:</b> {esc(analisi["durata_video"])}'
        f'{riga_salmo}</div>',
        unsafe_allow_html=True,
    )

    if salmo:
        if st.button("\U0001F4D6 Aggiungi anche gli inni sul Salmo", use_container_width=True):
            query = costruisci_query(estrai_parole_chiave(testo, 3), "Lodi pentecostali / ADI")
            query += query_per_salmo(salmo)
            st.session_state["query_usate"] = query
            with st.spinner("\U0001F50D Cerco gli inni dedicati a questo Salmo..."):
                try:
                    risultati = ricerca_cached(tuple(query), 5, tuple(estrai_parole_chiave(testo, 3)))
                except Exception as exc:
                    st.error(f"\u26A0\uFE0F {exc}")
                    risultati = []
            st.session_state["risultati"] = risultati
            st.session_state["scelta"] = None
            st.rerun()

# --------------------------------------------------------------------------
# I versetti biblici trovati (dal pulsante "Trova il testo adatto")
# --------------------------------------------------------------------------

versetti = st.session_state.get("versetti") or []
if versetti:
    st.markdown(
        '<div class="step">Il testo biblico</div>'
        '<h3>\U0001F4D6 Versetti che parlano al tuo pensiero</h3>'
        f'<div class="note">Testo di riferimento: {esc(NOME_TRADUZIONE)}. '
        'Scegli il versetto che ti risuona: l\'app lo mette nella casella e cerca '
        'subito la canzone.</div>',
        unsafe_allow_html=True,
    )
    for i, v in enumerate(versetti, start=1):
        with st.container(border=True):
            chip = "".join(f'<span class="chip">{esc(t)}</span>' for t in v["temi"])
            st.markdown(
                f'<div class="badge">#{i}</div>'
                f'<div class="card-title">{esc(v["riferimento"])}</div>'
                f'<div class="card-meta" style="font-size:.92rem;opacity:.85;">'
                f'«{esc(v["testo"])}»</div>{chip}',
                unsafe_allow_html=True,
            )
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
        st.markdown(
            f'<div class="box"><b>Riferimento rilevato:</b> {esc(riferimento["riferimento"])}'
            f'<br><span class="note">Versione inglese per le ricerche: '
            f'{esc(riferimento["riferimento_en"])}</span></div>',
            unsafe_allow_html=True,
        )
        for passo in genera_passi(testo, st.session_state["analisi"], riferimento):
            st.markdown(
                f'<div class="box" style="margin-bottom:8px;">'
                f'<b>{esc(passo["titolo"])}</b><br>{esc(passo["contenuto"])}<br>'
                f'<span class="note"><i>Domanda guida: {esc(passo["domanda"])}</i></span>'
                f'</div>',
                unsafe_allow_html=True,
            )

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
                st.markdown(
                    f'<div class="card-title">{esc(r.titolo)}</div>'
                    f'<div class="card-meta">{esc(r.canale)}'
                    + (f' &bull; {esc(r.durata)}' if r.durata else "") + '</div>',
                    unsafe_allow_html=True,
                )
                c1, c2 = st.columns(2)
                with c1:
                    blocco_copia(r.titolo, f"studio{i}")
                with c2:
                    st.link_button("\U0001F3A7 Ascolta", r.url, use_container_width=True)

# ==========================================================================
# PASSAGGIO 2/3 - CERCA e SCEGLI
# ==========================================================================

risultati = st.session_state["risultati"]
query_usate = st.session_state["query_usate"]

if risultati:
    st.markdown('<hr>', unsafe_allow_html=True)
    st.markdown(
        '<div class="step">PASSAGGIO 2</div>'
        f'<h3>\U0001F3A4 {len(risultati)} canzoni trovate</h3>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="note">Copia il titolo e cercalo nella libreria audio di TikTok, '
        'oppure ascolta l\'anteprima qui sotto.</div>',
        unsafe_allow_html=True,
    )

    parole_chiave = estrai_parole_chiave(testo or "", max_parole=3)
    temi = (st.session_state["analisi"] or {}).get("temi", [])

    for i, r in enumerate(risultati, start=1):
        with st.container(border=True):
            st.markdown(
                f"""
                <div style="display:flex;gap:12px;align-items:flex-start;">
                  <img class="thumb" src="{r.url_miniature}" alt="" loading="lazy">
                  <div style="flex:1;min-width:0;">
                    <div class="badge">#{i}</div>
                    <div class="card-title">{esc(r.titolo)}</div>
                    <div class="card-meta">{esc(r.canale)}"""
                + (f" &bull; {esc(r.durata)}" if r.durata else "")
                + "</div></div></div>",
                unsafe_allow_html=True,
            )

            motivi = spiega_canzone(r.titolo, r.canale, r.durata, r.secondi,
                                    parole_chiave, temi)
            with st.expander("Perch\u00e9 questa canzone"):
                for motivo in motivi:
                    st.markdown(f'<div class="note">&bull; {esc(motivo)}</div>',
                                unsafe_allow_html=True)

            col_a, col_b = st.columns([1, 1])
            with col_a:
                blocco_copia(r.titolo, f"copia{i}")
            with col_b:
                st.link_button("\U0001F3A7 Ascolta", r.url, use_container_width=True)

            st.link_button(
                "\U0001F50D Cerca l'audio su TikTok",
                link_ricerca_audio(r.titolo),
                use_container_width=True,
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
            st.markdown(
                '<div class="box">'
                + "<br>".join(f"<b>{i+1}.</b> {esc(q)}" for i, q in enumerate(query_usate))
                + "</div>",
                unsafe_allow_html=True,
            )

# ==========================================================================
# PASSAGGIO 4 - PUBBLICA
# ==========================================================================

post = st.session_state["post"]
if post:
    st.markdown('<hr>', unsafe_allow_html=True)
    st.markdown(
        '<div class="step">PASSAGGIO 3</div><h3>\U0001F4E4 Prepara e pubblica</h3>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="box"><b>\U0001F3B5 Canzone scelta:</b> {esc(post["titolo"])}'
        f'<br><span class="note">Canale: {esc(post["canale"])}</span></div>',
        unsafe_allow_html=True,
    )

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
    st.markdown('<div class="note" style="margin-top:10px;"><b>\U0001F4C5 '
                'Quando lo pubblichi?</b></div>', unsafe_allow_html=True)
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
    st.markdown(
        f'<div class="box box-ok">\U0001F4C5 <b>{giorno_settimana(data_pub)} '
        f'{data_pub.strftime("%d/%m/%Y")} alle {ora_pub}</b><br>'
        f'<span class="note">{esc(motivo)}</span></div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="note" style="margin-bottom:4px;"><b>Hashtag suggeriti:</b></div>'
        + "".join(f'<span class="chip">{esc(h)}</span>' for h in hashtag),
        unsafe_allow_html=True,
    )

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
        st.markdown(
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
            """,
            unsafe_allow_html=True,
        )

    with st.expander("\U0001F4F1 Come si pubblica dal telefono (5 passaggi)"):
        st.markdown(
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
            """,
            unsafe_allow_html=True,
        )

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
        st.session_state["archivio"] = aggiungi_post(voce)
        st.success("\u2705 Post salvato nell'archivio: lo ritrovi qui sotto.")

# ==========================================================================
# Informazioni: TikTok + come si usa + cronologia
# ==========================================================================

with st.expander("\U0001F517 Come funziona la ricerca su TikTok"):
    st.markdown(f'<div class="box box-warn">{esc(MESSAGGIO_TIKTOK)}</div>',
                unsafe_allow_html=True)
    st.markdown(
        '<div class="note">In più l\'app usa YouTube (ricerca pubblica, senza API '
        'a pagamento) per trovare i titoli reali delle canzoni pentecostali: sono '
        'gli stessi titoli che trovi nella libreria audio di TikTok.</div>',
        unsafe_allow_html=True,
    )

with st.expander("\U0001F4D6 Come si usa l'app (guida rapida)"):
    st.markdown(
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
        <b>5.</b> Tocca <b>"Scegli questa canzone per il post"</b>: si apre il
        pacchetto di pubblicazione con caption, hashtag, testo a schermo e piano
        del video.<br>
        <b>6.</b> Copia caption e hashtag, apri TikTok e pubblica.<br><br>
        <i>Se il testo è un Salmo, l'app lo riconosce (anche con la numerazione
        Vulgate) e aggiunge la ricerca degli inni dedicati a quel Salmo.</i>
        </div>
        """,
        unsafe_allow_html=True,
    )

cronologia = st.session_state["cronologia"]
if cronologia:
    with st.expander(f"\U0001F504 Cronologia ricerche ({len(cronologia)})"):
        for voce in cronologia:
            st.markdown(
                f'<div class="note"><b>{esc(voce["ora"])}</b> &mdash; {esc(voce["testo"])}'
                f'<br><i>parole chiave: {esc(voce["parole"])}</i></div>',
                unsafe_allow_html=True,
            )

# ==========================================================================
# IL MIO ARCHIVIO
# ==========================================================================

archivio = st.session_state["archivio"] or []
st.markdown('<hr>', unsafe_allow_html=True)
st.markdown(
    '<div class="step">ARCHIVIO</div><h3>\U0001F5C2 Post pronti da pubblicare</h3>',
    unsafe_allow_html=True,
)

if not archivio:
    st.markdown(
        '<div class="note">Qui trovi tutto quello che prepari: canzone, caption, '
        'hashtag e data di pubblicazione. Resta salvato anche se chiudi il browser.'
        '<br><br><i>(Nel passaggio 3, tocca "Salva nell\'archivio")</i></div>',
        unsafe_allow_html=True,
    )
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
            st.markdown(
                f'<div class="badge">{esc(badge)} &bull; {esc(scelta_data)} '
                f'alle {esc(voce.get("ora", ""))}</div>'
                f'<div class="card-title">\U0001F3B5 {esc(voce.get("canzone", ""))}</div>'
                f'<div class="card-meta">{esc(voce.get("testo", "")[:90])}</div>',
                unsafe_allow_html=True,
            )
            with st.expander("Vedi tutto"):
                st.markdown(
                    f'<div class="box"><b>Testo a schermo:</b> {esc(voce.get("hook", ""))}'
                    f'<br><br><b>Caption:</b><br>{esc(voce.get("caption", ""))}'
                    f'<br><br><b>Hashtag:</b> {esc(" ".join(voce.get("hashtag", [])))}</div>',
                    unsafe_allow_html=True,
                )
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
                    st.session_state["archivio"] = elimina_post(voce.get("id", ""))
                    st.rerun()

st.markdown(
    '<div class="note" style="text-align:center;margin-top:18px;">'
    'Fatto per i creator cristiani \U0001F49F</div>',
    unsafe_allow_html=True,
)

# --- DIAGNOSTICA TEMPORANEA (verifica scraping da Cloud) ---
if not st.session_state.get("_diag"):
    st.session_state["_diag"] = True
    try:
        _r = ricerca_cached(("musica evangelica pentecostale lode",), 3, ("lode",))
        st.session_state["_diag_esito"] = f"DIAG: {len(_r)} risultati | " + (
            _r[0].titolo[:60] if _r else "NESSUN RISULTATO (YouTube blocca?)")
    except Exception as _e:
        st.session_state["_diag_esito"] = f"DIAG ERRORE: {_e}"
st.markdown(f"### {st.session_state.get('_diag_esito', 'DIAG: ...')}")
