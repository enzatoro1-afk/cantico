lines = open('app.py', encoding='utf-8').read().split('\n')

# Trova l'inizio e la fine del blocco PASSAGGIO 2
passaggio2_start = None
passaggio2_end = None
for i in range(len(lines)):
    if 'PASSAGGIO 2 - CERCA SU TIKTOK' in lines[i].strip():
        passaggio2_start = i
    if passaggio2_start is not None and '---- CANZONE ORIGINALE' in lines[i].strip():
        passaggio2_end = i
        break

if passaggio2_start is None or passaggio2_end is None:
    print("Errore: blocco PASSAGGIO 2 non trovato")
    exit(1)

print(f"PASSAGGIO 2 trovato: righe {passaggio2_start+1} a {passaggio2_end-1}")
block = lines[passaggio2_start:passaggio2_end]  # esclude la riga "CANZONE ORIGINALE"

# Trova dove inserire il blocco: prima di "IL POST TIKTOK"
insert_pos = None
for i in range(len(lines)):
    if '---- IL POST TIKTOK ----' in lines[i].strip():
        insert_pos = i
        break

if insert_pos is None:
    print("Errore: sezione IL POST TIKTOK non trovata")
    exit(1)

print(f"Inserire PASSAGGIO 2 prima della riga {insert_pos+1} (IL POST TIKTOK)")

# Rimuovi il blocco PASSAGGIO 2 dalla posizione originale
del lines[passaggio2_start:passaggio2_end]

# Inserisci il blocco nella nuova posizione (slice assignment)
lines[insert_pos:insert_pos] = block

# Salvataggio
open('app.py', 'w', encoding='utf-8').write('\n'.join(lines))
print("Riorganizzazione completata!")