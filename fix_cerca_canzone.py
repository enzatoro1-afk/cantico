lines = open('app.py', encoding='utf-8').read().split('\n')
# Find and replace the specific text
for i, l in enumerate(lines):
    if 'pentecostale, cerca la canzone giusta e ti prepara il post' in l:
        # Replace this line
        lines[i] = l.replace('pentecostale, cerca la canzone giusta e ', 'pentecostale e ')
        print(f'Replaced line {i+1}: {l[:80]} -> {lines[i][:80]}')
open('app.py', 'w', encoding='utf-8').write('\n'.join(lines))
print('File salvato')