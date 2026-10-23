lines = open('app.py', encoding='utf-8').read().split('\n')

# Sostituisco il blocco PASSAGGIO 2 (da riga 3214 a 3238 circa) con una versione semplificata
# Il nuovo testo sarà più breve e diretto

new_passaggio2 = [
    '',
    '# il titolo da cercare su TikTok: le parole chiave spirituali del versetto',
    '_parole_tiktok = []',
    'try:',
    '    _interp2 = (st.session_state.get("versetto_studio") or {}).get("interpretazione") or {}',
    '    _parole_tiktok = _interp2.get("parole_chiave") or []',
    'except Exception:',
    '    _parole_tiktok = []',
    'if not _parole_tiktok:',
    '    _parole_tiktok = estrai_parole_chiave(testo or "", 3)',
    '_query_tiktok = " ".join(_parole_tiktok[:3]).strip() or (testo or "").strip()[:60]',
    '',
    'html(\'<hr>\')',
    html(
        '<div class="step">PASSAGGIO 2</div>',
        '<h3>\U0001F50D Il titolo da cercare su TikTok</h3>'
    ),
    html(
        '<div class="note box-ok"><b>Perche\' questo titolo?</b> L\'app lo ricava '
        'dall\'interpretazione del tuo versetto: sono le parole spirituali del passaggio. '
        'Su TikTok cerca <b>questo titolo</b> nella libreria audio e trovi il suono originale.</div>'
    ),
    html(
        f'<div class="box"><b>Titolo da cercare:</b> {esc(_query_tiktok)}</div>'
    ),
    blocco_copia(_query_tiktok, "copia_titolo_tiktok",
                 "\U0001F4CB Copia il titolo per TikTok"),
    st.link_button(
        "\U0001F50A Cerca questo titolo su TikTok",
        f"https://www.tiktok.com/search?q={_quote_url(_query_tiktok)}",
        use_container_width=True,
        type="primary"
    ),
    st.caption("Si apre la ricerca di TikTok: da li' scegli il suono originale "
               "(non il video di un altro). Se TikTok ti manda alla home, "
               "accedi col tuo account e riprova il link."),
    # RIMOSSO il "percorsi completo (5 secondi)" e i passaggi manuali per semplificare
]

# Trova la posizione esatta dove inserire (prima di html('<hr>') che segna la fine vecchio blocco vecchio)
# In realtà dobbiamo sostituire dal punto in cui inizia il nuovo testo vecchio fino a prima di CANZONE ORIGINALE

# Trova inizio blocco vecchio: cerca 'html('<hr>')' dopo il box ok
# In realtà cerchiamo di sostituire da riga 3214 (il primo html con step) alla riga 3238 circa

# Trova posizione di partenza: la riga con '<div class="step">PASSAGGIO 2</div>'
start_search = None
for i in range(len(lines)):
    if lines[i].strip() == '<div class="step">PASSAGGIO 2</div>':
        start_search = i
        break

if start_search is None:
    print("Errore: non trovato inizio PASSAGGIO 2")
    exit(1)

# Trova fine blocco: la riga prima di '# =========================================================================='
# che precede '---- CANZONE ORIGINALE'
end_search = None
for i in range(start_search, len(lines)):
    if '# ---- CANZONE ORIGINALE' in lines[i].strip():
        end_search = i
        break

if end_search is None:
    print("Errore: non trovato fine PASSAGGIO 2")
    exit(1)

print(f"Rimozione PASSAGGIO 2 vecchio: righe {start_search+1} a {end_search}")

# Rimuovo il vecchio blocco
del lines[start_search:end_search]

# Inserisco il nuovo blocco semplificato
# Inserisco dopo la riga start_search-1 (che è una riga vuota o commento)
# Il nuovo blocco comincia con '' (riga vuota) poi il codice

# Trova dove inserire: dopo la riga start_search-1
insert_pos = start_search  # Iniziamo da questa posizione

# Il nuovo blocco ha queste righe (già pronto nella variabile new_passaggio2)
# new_passaggio2 è una lista di righe da inserire

# Usa slice assignment per inserire
lines[insert_pos:insert_pos] = new_passaggio2

# Salvataggio
open('app.py', 'w', encoding='utf-8').write('\n'.join(lines))
print("Semplificazione PASSAGGIO 2 completata!")