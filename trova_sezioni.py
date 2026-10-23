lines = open('app.py', encoding='utf-8').read().split('\n')
# cerca FASE 2 o sezione 'cerca canzone' o 'SELEZIONA CANZONE'
for i in range(len(lines)):
    l = lines[i].strip()
    low = l.lower()
    # pattern che indicano la sezione di ricerca canzone
    if any(k in low for k in [
        'cerca la canzone', 
        'scegli la canzone',
        'SELEZIONA',
        'FASE 2:',
        'musica forc',
        'FASE 1: studio',
    ]) and i < 900:
        print(f'{i+1}: {l[:100]}')