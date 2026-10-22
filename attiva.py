# -*- coding: utf-8 -*-
"""
attiva.py
=========
Il pannello "Attiva tutto": per ogni servizio che puo' sbloccare l'app,
dice (1) se e' gia' attivo, (2) come si prende la chiave, (3) un pulsante
per incollarla dal clipboard, (4) un pulsante che la VERIFICA davvero.

Due modi per usare una chiave:
  - la chiave DELL'APP (nei Secrets di Streamlit): la mette il proprietario
    e serve a TUTTI quelli che usano l'app. Nessuna operazione per l'utente.
  - la chiave PERSONALE: la mette l'utente nel suo browser, resta privata
    e non consuma la quota degli altri.

Nessuna password viene mai richiesta: le chiavi si creano dal sito del
servizio (serve il login dell'utente) e l'app le verifica e le conserva.
"""

from __future__ import annotations

import json
import os

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore


# --------------------------------------------------------------------------
# Lo script che prende la chiave dal CLIPBOARD e la mette nel campo
# --------------------------------------------------------------------------
SCRIPT_CLIPBOARD = """
<script>
(function () {
  if (!navigator.clipboard || !navigator.clipboard.readText) return;
  var etichetta = "__ETICHETTA__";
  navigator.clipboard.readText().then(function (testo) {
    if (!testo || texto.length < 8) return;
    var campi = document.querySelectorAll('input[type="password"], input[type="text"]');
    for (var i = 0; i < campi.length; i++) {
      var lab = campi[i].closest('div[data-testid="stTextInput"]');
      if (lab && lab.innerText && lab.innerText.indexOf(etichetta) >= 0) {
        if (campi[i].value) return;
        var proto = Object.getPrototypeOf(campi[i]);
        var setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
        setter.call(campi[i], testo.trim());
        campi[i].dispatchEvent(new Event('input', { bubbles: true }));
        return;
      }
    }
  }).catch(function () {});
})();
</script>
"""


def _segreto(nome: str) -> str:
    """Legge un segreto di Streamlit senza rompere nulla se manca."""
    try:
        import streamlit as st
        return str(st.secrets.get(nome, "") or "").strip()
    except Exception:
        pass
    try:
        import tomllib
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         ".streamlit", "secrets.toml")
        if os.path.exists(p):
            with open(p, "rb") as f:
                return str(tomllib.load(f).get(nome, "") or "").strip()
    except Exception:
        pass
    return str(os.environ.get(nome, "") or "").strip()


# --------------------------------------------------------------------------
# Le verifiche vere (si chiamano il servizio e guardano la risposta)
# --------------------------------------------------------------------------

def verifica_gemini(chiave: str) -> tuple:
    """La chiave Gemini funziona davvero? Risponde con una parola."""
    if not chiave:
        return False, "nessuna chiave"
    if requests is None:
        return False, "requests non installato"
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=chiave)
        risp = client.models.generate_content(
            model="gemini-2.0-flash",
            contents="Rispondi SOLO con la parola: pronto",
            config=types.GenerateContentConfig(max_output_tokens=10),
        )
        testo = (risp.text or "").strip()
        if testo:
            return True, "Gemini risponde: tutto pronto"
        return False, "Gemini non ha risposto"
    except Exception as exc:
        return False, f"Gemini: {str(exc)[:120]}"


def verifica_treblo(chiave: str) -> tuple:
    """La chiave Treblo funziona? Quanti crediti restano?"""
    if not chiave:
        return False, "nessuna chiave"
    if requests is None:
        return False, "requests non installato"
    try:
        r = requests.get("https://api.treblo.com/v1/credits/balance",
                         headers={"Authorization": f"Bearer {chiave}"},
                         timeout=25)
        if r.status_code == 200:
            d = r.json() or {}
            crediti = d.get("credits", d.get("balance"))
            return True, f"Treblo attivo: {crediti} crediti"
        if r.status_code in (401, 403):
            return False, "chiave Treblo non valida"
        return False, f"Treblo ha risposto {r.status_code}"
    except Exception as exc:
        return False, f"Treblo: {str(exc)[:100]}"


def verifica_huggingface(token: str) -> tuple:
    """Il token Hugging Face funziona?"""
    if not token:
        return False, "nessun token"
    if requests is None:
        return False, "requests non installato"
    try:
        r = requests.get("https://huggingface.co/api/whoami-v2",
                         headers={"Authorization": f"Bearer {token}"},
                         timeout=25)
        if r.status_code == 200:
            d = r.json() or {}
            nome = d.get("name") or d.get("fullname") or "l'utente"
            return True, f"Hugging Face attivo ({nome})"
        if r.status_code in (401, 403):
            return False, "token Hugging Face non valido"
        return False, f"Hugging Face ha risposto {r.status_code}"
    except Exception as exc:
        return False, f"Hugging Face: {str(exc)[:100]}"


def verifica_suno() -> tuple:
    """Suno e' collegato (cookie presente e valido)?"""
    try:
        import suno
        ok, nota = suno.suno_disponibile()
        return ok, nota
    except Exception as exc:
        return False, str(exc)[:100]


# --------------------------------------------------------------------------
# Il pannello
# --------------------------------------------------------------------------

def pannello(st, html_fn, esc_fn):
    """
    Mostra il pannello "Attiva tutto".

    - per ogni servizio: stato, link per registrarsi, campo per la chiave,
      pulsante "dal clipboard" e pulsante "verifica"
    - se la chiave dell'APP c'e' (nei Secrets), lo dice: e' gia' attivo
      per tutti e l'utente non deve fare nulla
    """
    st.markdown("### ⚙️ Attiva tutto (2 minuti)")
    html_fn(
        '<div class="note">Qui sotto trovi tutto quello che serve per far '
        'andare l\'app al massimo. <b>Se una riga è già verde</b>, non devi '
        'fare niente: la chiave ce l\'ha già l\'app (la usa per tutti). '
        'Se è arancora, ci metti 1-2 minuti.<br><br>'
        '<b>Niente carta di credito, niente pagamenti:</b> le chiavi qui '
        'sotto sono tutte gratis e si prendono con un account gratuito. '
        '(L\'unica che chiede la carta è Treblo, e serve solo se vuoi usare '
        'quello: anche lì non ti addebitano nulla, ma è una verifica.)</div>')

    _servizi = [
        {
            "nome": "Google Gemini",
            "per": "l'interpretazione profonda e le parole del brano",
            "link": "https://aistudio.google.com/api-keys",
            "come": "Accendi con Google → «Create API key» → copia la chiave",
            "chiave": "GEMINI_API_KEY",
            "sessione": "chiave_gemini",
            "campo": "Chiave Google Gemini (incolla qui)",
            "verifica": verifica_gemini,
            "facoltativa": False,
        },
        {
            "nome": "Treblo",
            "per": "la canzone CANTATA (e il video .mp4) - 3.000 crediti, "
                   "ma chiede di verificare la carta",
            "link": "https://treblo.com/developers/account",
            "come": "Accedi con Google → «Create API key» → copia la chiave",
            "chiave": "TREBLO_API_KEY",
            "sessione": "chiave_treblo",
            "campo": "Chiave Treblo (incolla qui)",
            "verifica": verifica_treblo,
            "facoltativa": True,
        },
        {
            "nome": "Hugging Face",
            "per": "ACE-Step: un'altra canzone cantata, open source",
            "link": "https://huggingface.co/settings/tokens",
            "come": "«New token» → nome a piacere → Read → copia",
            "chiave": "HF_TOKEN",
            "sessione": "token_hf",
            "campo": "Token Hugging Face (incolla qui)",
            "verifica": verifica_huggingface,
            "facoltativa": True,
        },
    ]

    for _s in _servizi:
        _comune = str(_segreto(_s["chiave"]) or "").strip()
        _personale = str(st.session_state.get(_s["sessione"], "") or "").strip()
        _attiva = bool(_comune or _personale)

        with st.container(border=True):
            _c1, _c2 = st.columns([3, 1])
            with _c1:
                st.markdown(f"**{_s['nome']}** — {_s['per']}")
                if _comune:
                    st.success("✅ attivo per tutti (è la chiave dell'app)")
                elif _personale:
                    st.success("✅ attivo con la tua chiave (privata)")
                else:
                    st.warning("❌ non ancora attivo"
                               + (" (facoltativo)" if _s["facoltativa"] else ""))
            with _c2:
                st.link_button("Registrati ↗", _s["link"],
                               use_container_width=True)

            if _comune and _s["sessione"] == "chiave_treblo":
                if st.button("\U0001F5D1 Togli la chiave dal server",
                             key="togli_treblo_server",
                             use_container_width=True):
                    import treblo as _treblo_mod
                    _treblo_mod.dimentica_chiave()
                    st.rerun()

            if not _comune:
                # il campo per la chiave personale
                _valore = st.text_input(
                    _s["campo"], type="password", key="attiva_" + _s["sessione"],
                    placeholder="incolla qui la chiave",
                    help=_s["come"])
                _c3, _c4 = st.columns(2)
                with _c3:
                    html_fn(SCRIPT_CLIPBOARD.replace("__ETICHETTA__",
                                                    _s["campo"]), js=True)
                    if st.button("📋 Prendi dal clipboard",
                                 key="clip_" + _s["sessione"],
                                 use_container_width=True):
                        st.info("Copia la chiave (Ctrl+C) e premi di nuovo "
                                "questo pulsante.")
                with _c4:
                    if st.button("🔎 Verifica", key="ver_"+
                                 _s["sessione"], use_container_width=True):
                        _k = _valore.strip()
                        if _k:
                            st.session_state[_s["sessione"]] = _k
                            _ok, _nota = _s["verifica"](_k)
                            (st.success if _ok else st.error)(_nota)
                        else:
                            st.info("Incolla prima la chiave.")
                    if st.checkbox("Condividi con TUTTI gli utenti dell'app "
                                   "(la quota sara' di tutti)",
                                   key="condividi_" + _s["sessione"],
                                   value=False):
                        if _valore.strip():
                            _ok2 = False
                            try:
                                if _s["sessione"] == "chiave_treblo":
                                    import treblo as _mod
                                    _ok2 = _mod.ricorda_chiave(_valore.strip())
                                else:
                                    import musica as _mod
                                    _ok2 = _mod.ricorda_token_hf(
                                        _valore.strip())
                            except Exception:
                                _ok2 = False
                            if _ok2:
                                st.success("\u2705 Chiave salvata sul server: da "
                                           "ora in poi tutti possono fare le "
                                           "canzoni senza configurare nulla.")
                            else:
                                st.warning("Non sono riuscito a salvarla sul "
                                           "server.")

    # --- Suno: non usa una chiave API ma il login ---
    with st.container(border=True):
        _c1, _c2 = st.columns([3, 1])
        with _c1:
            st.markdown("**Suno** — i tuoi crediti gratuiti (300 al mese)")
            _ok_s, _nota_s = verifica_suno()
            if _ok_s:
                st.success("✅ collegato: " + _nota_s)
            else:
                st.warning("❌ non collegato (facoltativo)")
                st.caption("Suno non ha un'API pubblica per gli account "
                           "gratuiti: si usa il login del browser.")
        with _c2:
            st.link_button("Apri suno.com ↗", "https://suno.com/library",
                           use_container_width=True)
