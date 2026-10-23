lines = open('app.py', encoding='utf-8').read().split('\n')

# Find the exact line numbers to replace
# We need to replace lines 3058-3069 (1-indexed) which is 3057-3068 (0-indexed)

# Let's find the "Prima scegli la canzone" text
for i, l in enumerate(lines):
    if "Prima scegli la canzone" in l:
        print(f'Found at line {i+1}: {l[:80]}')
        # Now replace from this line onwards until the else block ends
        # The old code is from line i to around line i+11
        # Let's be more precise: replace from " _post_gia = st.session_state.get("post")" 
        # to the end of the else block
        
        # Actually, let's just replace the specific old string we know
        pass

# Better approach: use the write tool to do the replacement
# Read the file content
content = open('app.py', encoding='utf-8').read()

# Old string to replace (the exact block)
old_string = '''            _post_gia = st.session_state.get("post")
            if not _post_gia:
                st.info("Prima scegli la canzone (pulsante "
                        "'\\u2B50 Scegli questa canzone per il post'): poi "
                        "torna qui e usa la caption dell'IA.")
            else:
                _post_gia = dict(_post_gia)
                _post_gia["caption"] = _post_ia.get("caption", "")
                _post_gia["hook"] = _post_ia.get("hook", "")
                _post_gia["riflessione"] = _rif_ia.get("riflessione", "")
                _post_gia["corpo_ia"] = _post_ia.get("corpo", [])
                _post_gia["cta_ia"] = _post_ia.get("cta", "")
                _post_gia["momento_ia"] = _post_ia.get("momento", {})'''

# New string
new_string = '''            _post_gia = st.session_state.get("post")
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
            else:
                _post_gia = dict(_post_gia)
                _post_gia["caption"] = _post_ia.get("caption", "")
                _post_gia["hook"] = _post_ia.get("hook", "")
                _post_gia["riflessione"] = _rif_ia.get("riflessione", "")
                _post_gia["corpo_ia"] = _post_ia.get("corpo", [])
                _post_gia["cta_ia"] = _post_ia.get("cta", "")
                _post_gia["momento_ia"] = _post_ia.get("momento", {})'''

if old_string in content:
    content = content.replace(old_string, new_string)
    open('app.py', 'w', encoding='utf-8').write(content)
    print('Rimpiazionato con successo')
else:
    print('Old string non trovato - ricerca manuale')
    # Debug: cerca parti della stringa
    for i, line in enumerate(content.split('\n')):
        if 'post_gia' in line and 'session_state' in line:
            print(f'Line {i+1}: {line[:100]}')