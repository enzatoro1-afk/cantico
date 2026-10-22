# -*- coding: utf-8 -*-
"""
setup_app.py
============
CONFIGURAZIONE PER UTENTE: ognuno apre l'app, mette la SUA email, la SUA
password e le SUO chiavi API, e l'app gli si prepara da sola.

Come funziona:
1. **Chi sei**: email + password (serve per riaprire le tue impostazioni su
   questo dispositivo: nessun altro che usa il tuo telefono le vede).
2. **Le tue API**: per ogni servizio un pulsante che apre la pagina
   ufficiale dove si crea la chiave, il campo dove la incolli (e la puoi
   incollare anche dal clipboard con un tocco) e un pulsante "Verifica" che
   la prova davvero.
3. **Salva la tua app**: tutto viene salvato **nel browser** (localStorage),
   mai sul server e mai su GitHub. La quota di ogni servizio resta di chi
   ha creato la chiave.

Nessuna chiave del proprietario dell'app e' richiesta: ognuno parte da
zero e l'app gli si configura da sola.
"""

from __future__ import annotations

import hashlib
import json

# --------------------------------------------------------------------------
# I SERVIZI: per ognuno, la pagina dove si crea la chiave
# --------------------------------------------------------------------------

SERVIZI = (
    {
        "id": "gemini",
        "nome": "Google Gemini",
        "perche": ("scrive l'interpretazione e la riflessione: e' la piu' "
                   "importante, e' gratis"),
        "url": "https://aistudio.google.com/apikey",
        "dove": "clicca \"Create API key\" e copiala",
        "etichetta": "la tua chiave Gemini",
        "esempio": "AIza...",
        "obbligatoria": True,
    },
    {
        "id": "treblo",
        "nome": "Treblo",
        "perche": ("fa CANTARE la canzone con le tue parole e ti lascia "
                   "scaricare l'audio (quindi il video si fa tutto da solo)"),
        "url": "https://treblo.com/developers/account",
        "dove": "apri la sezione API e crea una chiave",
        "etichetta": "la tua chiave Treblo",
        "esempio": "sk_...",
        "obbligatoria": False,
    },
    {
        "id": "hf",
        "nome": "Hugging Face",
        "perche": ("serve ai modelli open source (ACE-Step, MusicGen): senza, "
                   "questi motori non partono"),
        "url": "https://huggingface.co/settings/tokens",
        "dove": "clicca \"New token\" -> \"Read\" e copialo",
        "etichetta": "il tuo token Hugging Face",
        "esempio": "hf_...",
        "obbligatoria": False,
    },
)

# come sono chiamate le chiavi nel localStorage del browser
STORAGE = {
    "gemini": "cantico_chiave_gemini",
    "treblo": "cantico_chiave_treblo",
    "hf": "cantico_token_hf",
    "email": "cantico_setup_email",
    "hash": "cantico_setup_hash",
    "fatto": "cantico_setup_fatto",
}


# --------------------------------------------------------------------------
# GLI SCRIPT (girano nel browser)
# --------------------------------------------------------------------------

# Riempie i campi con quello che e' gia' salvato nel browser.
# NB: si esegue UNA volta sola per pagina: se lo rifacessimo a ogni rerun,
# l'evento 'input' rilancierebbe l'app all'infinito.
SCRIPT_LEGGI_SETUP = """
<script>
(function () {
  try {
    if (window.__canticoSetupMesso) return;
    window.__canticoSetupMesso = true;
    function metti(marca, valore) {
      if (!valore) return false;
      var campi = document.querySelectorAll('input[type="password"], input[type="text"]');
      for (var i = 0; i < campi.length; i++) {
        var lab = campi[i].closest('div[data-testid="stTextInput"]');
        var testo = (lab && lab.innerText) || "";
        if (testo.indexOf(marca) < 0) continue;
        if (campi[i].value) return true;
        var proto = Object.getPrototypeOf(campi[i]);
        var setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
        setter.call(campi[i], valore);
        campi[i].dispatchEvent(new Event('input', { bubbles: true }));
        return true;
      }
      return false;
    }
    metti("La tua email", localStorage.getItem("cantico_setup_email"));
    metti("chiave Gemini", localStorage.getItem("cantico_chiave_gemini"));
    metti("chiave Treblo", localStorage.getItem("cantico_chiave_treblo"));
    metti("token Hugging Face", localStorage.getItem("cantico_token_hf"));
  } catch (e) {}
})();
</script>
"""

# Salva tutto nel browser e lascia un cookie (cosi' l'app sa che questo
# browser e' gia' configurato).
SCRIPT_SALVA_SETUP = """
<script>
(function () {
  try {
    localStorage.setItem("cantico_setup_email", "__EMAIL__");
    localStorage.setItem("cantico_setup_hash", "__HASH__");
    localStorage.setItem("cantico_setup_fatto", "1");
    __CHIAVI__
    document.cookie = "cantico_setup=1; path=/; max-age=31536000; SameSite=Lax";
  } catch (e) {}
})();
</script>
"""

# Il tasto "incolla dal clipboard": dopo il clic, lo script legge gli
# appunti e mette il testo nel campo giusto. Se il browser non permette,
# l'utente incolla a mano (Ctrl+V) e la verifica glielo dice.
SCRIPT_INCOLLA = """
<script>
(function () {
  try {
    if (!navigator.clipboard || !navigator.clipboard.readText) return;
    var valore = "";
    navigator.clipboard.readText().then(function (t) {
      valore = (t || "").trim();
      if (!valore) return;
      var campi = document.querySelectorAll('input[type="password"], input[type="text"]');
      for (var i = 0; i < campi.length; i++) {
        var lab = campi[i].closest('div[data-testid="stTextInput"]');
        var testo = (lab && lab.innerText) || "";
        if (testo.indexOf("__MARCA__") < 0) continue;
        if (campi[i].value) return;
        var proto = Object.getPrototypeOf(campi[i]);
        var setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
        setter.call(campi[i], valore);
        campi[i].dispatchEvent(new Event('input', { bubbles: true }));
        return;
      }
    }).catch(function () {});
  } catch (e) {}
})();
</script>
"""


def _hash_password(password: str) -> str:
    """Hash SHA-256 della password: nel browser non si salva in chiaro."""
    return hashlib.sha256((password or "").encode("utf-8")).hexdigest()


def _script_salva(email: str, hash_pw: str, chiavi: dict) -> str:
    """Costruisce lo script che salva tutto nel browser."""
    _pezzi = []
    for _id, _chiave in (("gemini", "cantico_chiave_gemini"),
                         ("treblo", "cantico_chiave_treblo"),
                         ("hf", "cantico_token_hf")):
        _v = str(chiavi.get(_id, "") or "").replace("\\", "\\\\").replace('"', '\\"')
        if _v:
            _pezzi.append(f'localStorage.setItem("{_chiave}", "{_v}");')
    return (SCRIPT_SALVA_SETUP
            .replace("__EMAIL__", str(email or "").replace("\\", "\\\\")
                     .replace('"', '\\"'))
            .replace("__HASH__", str(hash_pw or ""))
            .replace("__CHIAVI__", " ".join(_pezzi)))


# --------------------------------------------------------------------------
# IL PANNELLO DI CONFIGURAZIONE
# --------------------------------------------------------------------------

def _cookie_setup() -> bool:
    """True se questo browser e' gia' stato configurato."""
    try:
        import streamlit as st
        return bool(str(st.context.cookies.get("cantico_setup", "") or "").strip())
    except Exception:
        return False


def pannello_setup(st, html, esc, _direzione_musicale=None) -> dict:
    """
    Il pannello "Configura la tua app".

    Restituisce un dizionario con le chiavi raccolte:
      {"email": str, "hash": str, "gemini": str, "treblo": str, "hf": str,
       "salvato": bool}
    """
    _risultato = {"email": "", "hash": "", "gemini": "", "treblo": "",
                   "hf": "", "salvato": False}

    html(SCRIPT_LEGGI_SETUP, js=True)

    # ---- PASSO 1: chi sei ----
    with st.container(border=True):
        st.markdown("**Passo 1 — Chi sei**")
        st.markdown(
            '<div class="note">La tua email (per i tuoi account) e una '
            'password per la tua app: serve per riaprire le tue impostazioni '
            'su questo dispositivo. Resta <b>nel tuo browser</b> (non in '
            'chiaro) e nessun altro che usa il tuo telefono la vede.</div>',
            unsafe_allow_html=True)
        _email = st.text_input("La tua email (serve per i tuoi account)",
                               placeholder="nome@email.it", key="setup_email")
        _pw = st.text_input("Scegli una password per la tua app",
                             type="password", placeholder="almeno 6 caratteri",
                             key="setup_password",
                             help="Serve per riaprire le tue impostazioni su "
                                  "questo dispositivo. Resta nel tuo "
                                  "browser (non in chiaro) e nessun altro "
                                  "che usa il tuo telefono la vede.")
        if _email and _pw and len(_pw.strip()) >= 6:
            st.markdown('<div class="note box-ok">\u2705 Email e password '
                        'pronote.</div>', unsafe_allow_html=True)
    _risultato["email"] = (_email or "").strip()
    _risultato["hash"] = _hash_password(_pw or "")

    # ---- PASSO 2: le tue API ----
    st.markdown("---")
    with st.container(border=True):
        st.markdown("**Passo 2 — Le tue chiavi**")
        st.markdown(
            '<div class="note">Per ogni servizio: <b>1)</b> apri la pagina '
            'ufficiale, <b>2)</b> crea la chiave e copiala, <b>3)</b> torna '
            'qui, premi <b>"Incolla"</b> (la mette da sola) e poi '
            '<b>"Verifica"</b>.<br>Le chiavi restano <b>nel tuo browser</b>: '
            'la quota e\' tua e nessun altro la consuma.</div>',
            unsafe_allow_html=True)
        for _s in SERVIZI:
            _id = _s["id"]
            with st.expander(f"{_s['nome']} — {_s['perche'][:46]}",
                             expanded=(_id == "gemini")):
                st.markdown(
                    f'<div class="note">{_s["perche"]}<br>'
                    f'<b>1)</b> <a href="{_s["url"]}" target="_blank">'
                    f'apri {_s["url"]}</a> &rarr; {_s["dove"]}</div>',
                    unsafe_allow_html=True)
                _campo = st.text_input(f"Incolla qui { _s['etichetta'] }",
                                       type="password",
                                       placeholder=_s["esempio"],
                                       key=f"setup_{_id}")
                _c1, _c2 = st.columns(2)
                with _c1:
                    if st.button(f"\U0001F4CB Incolla", key=f"setup_{_id}_incolla",
                                 use_container_width=True):
                        st.session_state[f"setup_incolla_{_id}"] = True
                        st.rerun()
                with _c2:
                    if st.button(f"\U0001F50E Verifica", key=f"setup_{_id}_verifica",
                                 use_container_width=True):
                        _v = (_campo or "").strip()
                        if not _v:
                            st.warning("Incolla prima la chiave \U0001F4D8")
                        else:
                            with st.spinner("Verifico..."):
                                _ok = _verifica_chiave(_id, _v, _direzione_musicale)
                            if _ok:
                                st.session_state[f"setup_ok_{_id}"] = True
                                st.success("\u2705 Funziona!")
                            else:
                                st.session_state[f"setup_ok_{_id}"] = False
                                st.error("Non ha risposto: ricontrolla di averla "
                                         "copiata per intero.")
                # il paste automatico dal clipboard (dopo il clic su "Incolla")
                if st.session_state.pop(f"setup_incolla_{_id}", False):
                    html(SCRIPT_INCOLLA.replace("__MARCA__",
                                                _s["etichetta"]), js=True)
                    st.info("Se non si e' riempito da sola, il browser non "
                            "permette di leggere gli appunti: incolla la "
                            "chiave a mano (tocca il campo e fai Ctrl+V).")
                if st.session_state.get(f"setup_ok_{_id}"):
                    st.markdown('<div class="note box-ok">\u2705 Chiave '
                                'verificata.</div>', unsafe_allow_html=True)
                _risultato[_id] = (_campo or "").strip()

    # ---- PASSO 3: salva ----
    st.markdown("---")
    with st.container(border=True):
        st.markdown("**Passo 3 — Salva la tua app**")
        st.markdown(
            '<div class="note">Tutto viene salvato <b>nel tuo browser</b>: '
            'la ritrovi la prossima volta, <b>non finisce sul server</b> e '
            '<b>non finisce su GitHub</b>. La tua app sara\' <b>solo tua</b>.'
            '</div>', unsafe_allow_html=True)
        if st.button("\U0001F4BE Salva la mia app", type="primary",
                     key="setup_salva", use_container_width=True):
            if not _risultato["email"]:
                st.warning("Prima l'email \U0001F4D8")
            elif not _risultato["hash"] or len((_pw or "").strip()) < 6:
                st.warning("Scegli una password per la tua app (almeno 6 "
                           "caratteri) \U0001F512")
            elif not _risultato["gemini"]:
                st.warning("Prima la chiave Gemini: e' quella che serve per "
                           "scrivere l'interpretazione \U0001F512")
            else:
                html(_script_salva(_risultato["email"], _risultato["hash"],
                                    _risultato), js=True)
                st.session_state["setup_fatto"] = True
                st.rerun()

    if st.session_state.get("setup_fatto"):
        st.success("\u2705 La tua app e' pronta! Ricarica la pagina e comincia "
                   "a scrivere il tuo versetto.")
    return _risultato


def _verifica_chiave(servizio_id: str, chiave: str, _direzione=None) -> bool:
    """Prova davvero la chiave: se risponde, e' buona."""
    try:
        if servizio_id == "gemini":
            from ai_client import interpreta_gemini
            _r = interpreta_gemini("Rispondi solo: pace", chiave=chiave,
                                   timeout=45)
            return bool(_r.get("testo"))
        if servizio_id == "treblo":
            from treblo import treblo_disponibile
            _ok, _nota = treblo_disponibile()
            return bool(_ok)
        if servizio_id == "hf":
            from musica import token_huggingface
            return bool(token_huggingface())
    except Exception:
        return False
    return False
