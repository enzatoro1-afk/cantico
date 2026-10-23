lines = open('app.py', encoding='utf-8').read().split('\n')

# Find the PASSAGGIO 2 block boundaries
# Start: line with '# PASSAGGIO 2 - CERCA SU TIKTOK'
# End: line before '# ---- CANZONE ORIGINALE'
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

print(f"Rimuovo PASSAGGIO 2 dalle righe {passaggio2_start+1} a {passaggio2_end}")

# Remove the block from its original position
passaggio2_block = lines[passaggio2_start:passaggio2_end]  # keep these lines
del lines[passaggio2_start:passaggio2_end]

# Find where to insert: before '# ---- IL POST TIKTOK ----'
insert_pos = None
for i in range(len(lines)):
    if '# ---- IL POST TIKTOK ----' in lines[i].strip():
        insert_pos = i
        break

if insert_pos is None:
    print("Errore: sezione IL POST TIKTOK non trovata")
    exit(1)

print(f"Inserisco PASSAGGIO 2 prima della riga {insert_pos+1} (IL POST TIKTOK)")

# Insert the block BEFORE insert_pos
# This means the block will appear at position insert_pos, shifting existing content down
lines[insert_pos:insert_pos] = passaggio2_block

# Salvataggio
open('app.py', 'w', encoding='utf-8').write('\n'.join(lines))
print("Riorganizzazione completata!")