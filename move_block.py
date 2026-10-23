lines = open('app.py', encoding='utf-8').read().split('\n')

# Find exact boundaries
# PASSAGGIO 2 starts at line with '# PASSAGGIO 2 - CERCA SU TIKTOK'
# PASSAGGIO 2 ends before '# ---- CANZONE ORIGINALE'
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

print(f"Righe PASSAGGIO 2: {passaggio2_start+1} a {passaggio2_end-1}")
passaggio2_block = lines[passaggio2_start:passaggio2_end]  # include la riga # PASSAGGIO 2

# Remove the block from original position
del lines[passaggio2_start:passaggio2_end]

# Find position to insert: BEFORE '# ---- IL POST TIKTOK ----'
insert_pos = None
for i in range(len(lines)):
    if '# ---- IL POST TIKTOK ----' in lines[i].strip():
        insert_pos = i
        break

if insert_pos is None:
    print("Errore: sezione IL POST TIKTOK non trovata")
    exit(1)

print(f"Inserire PASSAGGIO 2 prima della riga {insert_pos+1}")

# Insert the block at the correct position
# We insert BEFORE insert_pos, so the block appears before IL POST TIKTOK
lines[insert_pos:insert_pos] = passaggio2_block

# Salvataggio
open('app.py', 'w', encoding='utf-8').write('\n'.join(lines))
print("Spostamento completato!")