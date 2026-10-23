content = open('app.py', encoding='utf-8').read()

# Sostituisco il blocco "percorsi completi (5 secondi)" con uno più breve
# Dalle righe 3232-3240

old_block = '''<div class="note" style="margin-top:8px;">
    '<b>Il percorso completo (5 secondi):</b><br>
    '1) tocca "Copia il titolo per TikTok" (il titolo e\' negli appunti)<br>
    '2) apri TikTok sul telefono &rarr; tocca "+" (nuovo video)<br>
    '3) "Aggiungi suono" &rarr; incolla il titolo &rarr; scegli il suono<br>
    '4) registra il video con quel suono e pubblica.<br><br>
    '<b>Se non vuoi cercare niente:</b> vai qui sotto in "Crea una canzone
    'ORIGINALE" &rarr; "FAI TUTTO": l\'app ti prepara tutto (parole, 
    'canzone cantata, poster, video 9:16) e tu pubblichi.</div>'''

new_block = '''<div class="note" style="margin-top:8px;">
    '<b>Se non vuoi cercare niente:</b> vai qui sotto in "Crea una canzone
    'ORIGINALE" &rarr; "FAI TUTTO": l\'app ti prepara tutto (parole, 
    'canzone cantata, poster, video 9:16) e tu pubblichi.</div>'''

if old_block in content:
    content = content.replace(old_block, new_block)
    open('app.py', 'w', encoding='utf-8').write(content)
    print('Rimosso percorso completo (5 secondi) e sostituito con testo più breve')
else:
    print('Vecchio blocco non trovato')