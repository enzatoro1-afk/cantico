lines = open('app.py', encoding='utf-8').read().split('\n')

# Modifica 1: Semplifica la spiegazione nel PASSAGGIO 2 (intorno riga 3216)
# Sostituisco il testo box-ok con uno più breve

content = open('app.py', encoding='utf-8').read()

# Il vecchio testo (approssimativo, cercando pattern unici)
old = '''<div class="note box-ok"><b>Perche\' questo titolo?</b> L\'app lo ricava
dall\'interpretazione del tuo versetto: sono le parole spirituali che
parlano del cuore del passaggio. Su TikTok cerca <b>questo titolo</b>
nella libreria audio e trovi il suono originale.'''

new = '''<div class="note box-ok"><b>Perche\' questo titolo?</b> L\'app lo ricava
dall\'interpretazione del tuo versetto: sono le parole spirituali del passaggio. Su TikTok
cerca <b>questo titolo</b> nella libreria audio e trovi il suono originale.</div>'''

if old in content:
    content = content.replace(old, new)
    open('app.py', 'w', encoding='utf-8').write(content)
    print('Testo PASSAGGIO 2 semplificato')
else:
    print('Vecchio testo non trovato')
    # Prova con variante
    old2 = '''<div class="note box-ok"><b>Perche\' questo titolo?</b> L\'app lo ricava
dall\'interpretazione del tuo versetto: sono le parole spirituali che
parlano del cuore del passaggio. Su TikTok cerca <b>questo titolo</b>
nella libreria audio e trovi il suono originale.'''
    if old2 in content:
        content = content.replace(old2, new)
        open('app.py', 'w', encoding='utf-8').write(content)
        print('Testo PASSAGGIO 2 semplificato (variante)')
    else:
        print('Nessuna delle varianti trovate')