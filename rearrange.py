lines = open('app.py', encoding='utf-8').read().split('\n')

# Find the PASSAGGIO 2 block
passaggio2_start = None
passaggio2_end = None
for i in range(len(lines)):
    if '# PASSAGGIO 2 - CERCA SU TIKTOK' in lines[i].strip():
        passaggio2_start = i
    if passaggio2_start is not None and '# ---- CANZONE ORIGINALE' in lines[i].strip():
        passaggio2_end = i
        break

if passaggio2_start is None or passaggio2_end is None:
    print("Errore: blocco PASSAGGIO 2 non trovato")
    exit(1)

passaggio2_block = lines[passaggio2_start:passaggio2_end]  # include # PASSAGGIO 2
print(f"Rimosso blocco di {len(passaggio2_block)} righe dalla posizione originale")

# Rimuovi dal posto originale
del lines[passaggio2_start:passaggio2_end]

# Inserisci ALL'INIZIO della lista (prima di tutto il resto)
lines.insert(0, '')  # riga vuota all'inizio
lines[1:1] = passaggio2_block  # inserisci le righe dopo la riga vuota

# Salvataggio
open('app.py', 'w', encoding='utf-8').write('\n'.join(lines))
print("Blocco inserito all'inizio del file!")