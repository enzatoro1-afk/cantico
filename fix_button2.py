content = open('app.py', encoding='utf-8').read()

# Rintracciamo la sezione esatta del bottone usando la chiave corretta
old_section = '    if st.button("\U0001F4E4 Usa questo post per il mio TikTok",\n                         type="primary", use_container_width=True,\n                         key="usa_post_riflessione"):'

new_section = '    if st.button("\U0001F4E4 Usa questo post per il mio TikTok",\n                     type="primary", use_container_width=True,\n                     key="usa_post_riflessione")'

if old_section in content:
    content = content.replace(old_section, new_section)
    print('SUCCESS: Trovata e corretta la chiave del bottone')
else:
    print('NOTE: Chiave del bottone gia corretta o diversa')

# Ora sistemiamo il corpo del bottone - rimuoviamo la riga doppia e aggiungiamo st.rerun()
old_body = '_post_gia = st.session_state.get("post")\n                _post_gia = st.session_state.get("post")\n                if not _post_gia:'

new_body = '_post_gia = st.session_state.get("post")\n                if not _post_gia:'

if old_body in content:
    content = content.replace(old_body, new_body)
    print('SUCCESS: Rimossa la riga doppia _post_gia')
else:
    print('NOTE: La riga doppia potrebbe gia essere sistemata')

# Ora aggiungiamo st.rerun() dopo il st.success
old_success = 'st.success("\\u2705 Fatto: nel PASSAGGIO 3 trovi la caption e "'
new_success = 'st.success("\\u2705 Fatto: nel PASSAGGIO 3 trovi la caption e "'
new_success2 = '''st.success("\\u2705 Fatto: nel PASSAGGIO 3 trovi la caption e "
                           "il testo a schermo.")
            # FORZA il riavvio dell'app per rendere effettivi i cambiamenti di session state
            st.rerun()'''

# Proviamo il nuovo success con rerun
if 'st.success("\\u2705 Fatto: nel PASSAGGIO 3 trovi la caption e "' in content:
    # Sostituiamo la riga del success e aggiungiamo le righe seguenti
    # Ma dobbiamo fare attenzione a non sostituire troppo
    lines = content.split('\\n')
    # Cerchiamo la linea con st.success e aggiungiamo dopo
    for i, line in enumerate(lines):
        if '\\u2705 Fatto: nel PASSAGGIO 3 trovi la caption e "' in line:
            # Sostituiamo questa linea e aggiungiamo le seguenti
            lines[i] = 'st.success("\\u2705 Fatto: nel PASSAGGIO 3 trovi la caption e "')
            # Aggiungiamo le righe dopo
            indent = ' ' * 16
            lines.insert(i+1, indent + ' # FORZA il riavvio dell app per rendere effettivi i cambiamenti di session state')
            lines.insert(i+2, indent + ' st.rerun()')
            break
    content = '\\n'.join(lines)
    print('SUCCESS: Aggiunto st.rerun() dopo st.success')
else:
    print('NOTE: Formattazione success diversa')

# Scriviamo il file modificato
open('app.py', 'w', encoding='utf-8').write(content)
print('File app.py aggiornato')