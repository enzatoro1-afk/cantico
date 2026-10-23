lines = open('app.py', encoding='utf-8').read().split('\n')

# Il vecchio testo nelle righe 3215-3218 (0-indice: 3214-3217)
# Uniamo le 4 righe che formano il testo box-ok
old_text = (
    lines[3214] + lines[3215] + lines[3216] + lines[3217] + lines[3218]
)
# Ma actually each line has the repr, let me just work with the raw content

content = open('app.py', encoding='utf-8').read()

# Cerco il pattern unico nella riga 3215
# La riga 3215 inizia con '<div class="note box-ok"><b>Perche\\' questo titolo?</b> L\\'app lo ricava'
# Voglio sostituire tutto il blocco che va dalla riga 3215 alla 3218

# Il nuovo testo breve (una riga sola concatenata)
new_text_short = '<div class="note box-ok"><b>Perche\' questo titolo?</b> L\'app lo ricava dall\'interpretazione del tuo versetto: sono le parole spirituali del passaggio. Su TikTok cerca <b>questo titolo</b> nella libreria audio e trovi il suono originale.</div>'

# Sostituisco il contenuto vecchio con il nuovo
# Devo fare attenzione a sostituire solo quella parte
if new_text_short in content:
    # Trova la posizione e sostituisce
    # Ma è più facile sostituire le 4 righe unite
    old_combined = lines[3215] + lines[3216] + lines[3217] + lines[3218]
    if old_combined in content:
        content = content.replace(old_combined, new_text_short)
        # Ora rimuoviamo le righe vecchie e inseriamo la nuova
        # Rimuoviamo 4 righe (3215-3218) e inseriamo 1 riga
        del lines[3215:3219]  # 4 righe: 3215, 3216, 3217, 3219? Wait let's count
        # 3215, 3216, 3217, 3218 = 4 righe
        lines[3215:3219] = [new_text_short]
        print('Sostituito con successo')
    else:
        print('Old combined not found')
else:
    print('Nuovo testo breve non ideale per il matching')
    # Proviamo un approccio diverso: sostituisco solo la parte centrale
    # La parte che cambia è tra 'parlano del cuore del passaggio. Su TikTok cerca' e 'nella libreria audio'
    old_middle = 'parlano del cuore del passaggio. Su TikTok cerca <b>questo titolo</b>'
    new_middle = 'parlano spirituali del passaggio. Su TikTok cerca <b>questo titolo</b>'
    if old_middle in content:
        content = content.replace(old_middle, new_middle)
        open('app.py', 'w', encoding='utf-8').write(content)
        print('Sostituito il middle text')
    else:
        print('Middle text not found')