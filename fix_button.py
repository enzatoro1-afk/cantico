content = open('app.py', encoding='utf-8').read()

old_block = '''    if st.button("\U0001F4E4 Usa questo post per il mio TikTok",
                     type="primary", use_container_width=True,
                     key="usa_post_ia"):
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
'''

new_block = '''    if st.button("\U0001F4E4 Usa questo post per il mio TikTok",
                     type="primary", use_container_width=True,
                     key="usa_post_ia"):
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
            # FORZA il riavvio dell'app per rendere effettivi i cambiamenti di session state
            st.rerun()
'''

if old_block in content:
    content = content.replace(old_block, new_block)
    open('app.py', 'w', encoding='utf-8').write(content)
    print('SUCCESS: Fix applied')
else:
    print('FAIL: Old block not found')