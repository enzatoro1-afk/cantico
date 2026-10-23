content = open('app.py', encoding='utf-8').read()

# Sostituisco il "percorsi completi (5 secondi)" con una versione più breve
old_percorso = '''<div class="note" style="margin-top:8px;">
    '<b>Il percorso completo (5 secondi):</b><br>
    '1) tocca "Copia il titolo per TikTok" (il titolo e\' negli appunti)<br>
    '2) apri TikTok sul telefono &rarr; tocca "+" (nuovo video)<br>
    '3) "Aggiungi suono" &rarr; incolla il titolo &rarr; scegli il suono<br>
    '4) registra il video con quel suono e pubblica.<br><br>
    '<b>Se non vuoi cercare niente:</b> vai qui sotto in "Crea una canzone
    'ORIGINALE" &rarr; "FAI TUTTO": l\'app ti prepara tutto (parole, 
    'canzone cantata, poster, video 9:16) e tu pubblichi.</div>'''

new_percorso = '''<div class="note" style="margin-top:8px;">
    '<b>Se non vuoi cercare niente:</b> vai qui sotto in "Crea una canzone
    'ORIGINALE" &rarr; "FAI TUTTO": l\'app ti prepara tutto (parole, 
    'canzone cantata, poster, video 9:16) e tu pubblichi.</div>'''

if old_percorso in content:
    content = content.replace(old_percorso, new_percorso)
    open('app.py', 'w', encoding='utf-8').write(content)
    print('Rimosso percorso completo (5 secondi)')
else:
    print('Testo percorso completo non trovato')