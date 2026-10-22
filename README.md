# 🎵 Assistente Canzoni Pentecostali per TikTok

Web app (Python + Streamlit) per i creator cristiani: dalla Parola alla Lode. scrivi un versetto o una riflessione evangelica,
l'app trova la **canzone di musica evangelica pentecostale** più adatta, te la
spiega, e prepara tutto il post (caption, hashtag, testo a schermo, data e
ora di pubblicazione).

Funziona da browser, quindi è **perfetta per il telefono**.

---

## ✅ Cosa fa

| # | Funzione | Come funziona |
|---|----------|---------------|
| 1 | **Correzione grammaticale** | Controlla il testo con LanguageTool (API pubblica, gratuita) e propone le correzioni ("perche" -> "perché", "da" -> "dà"). Se la rete manca, usa un dizionario di errori italiani frequenti. |
| 2 | **Trova il testo biblico adatto** | Scrivi una parola, una frase o un pensiero e l'app cerca il **versetto** che meglio gli parla (motore a concetti: "perdonami" -> "perdona", "misericordia"...). Testo: **Sacra Bibbia - Versione Riveduta 2020** (traduzione protestante/evangelica, NON cattolica). Poi "Trova la canzone" passa al passo 5. |
| 3 | **Analisi del testo** | Riconosce temi (Consolazione, Proclamazione, Salvezza, Amore, Fede, Preghiera, Coraggio, Guarigione, Speranza, Umiltà, Paternità), suggerisce il tono, la durata del video e il formato del post. |
| 4 | **Riconoscimento dei Salmi** | Riconosce "Salmo 22,1", "Sal 23", "Psalm 23" e anche i testi noti ("Il Signore è il mio pastore"), con la doppia numerazione **Vulgate / ebraica**. Aggiunge la ricerca degli inni dedicati a quel Salmo. |
| 5 | **Ricerca della canzone** | Estrae 3 parole chiave, le unisce a "musica evangelica pentecostale lode" / "inno pentecostale" e cerca su YouTube (ricerca pubblica, **nessuna API a pagamento**). Ordina i risultati per attinenza reale. |
| 6 | **Spiegazione del perché** | Ogni canzone proposta spiega perché è adatta al tuo testo (parole chiave in comune, genere, durata, tema). |
| 7 | **Copia Titolo** | Un tocco e il titolo è negli appunti: basta cercarlo nella libreria audio di TikTok. |
| 8 | **Cerca su TikTok** | Apre la ricerca dei suoni di TikTok già impostata sul titolo esatto della canzone. |
| 9 | **Pacchetto pubblicazione** | Caption (4 formati), hashtag tematici, testo da mettere a schermo nei primi 3 secondi, piano del video secondario per secondo. |
| 10 | **Data e orario** | Scegli la data e ricevi l'orario consigliato per un contenuto religioso (mattina presto, pausa pranzo, sera, domenica mattina...). |
| 11 | **Archivio** | Tutti i post preparati restano salvati nell'app (in un file JSON), con download .txt e ricarica. |
| 12 | **Studio biblico** | Riconosce il riferimento (Giovanni 3,16), propone i **4 passi** dello studio induttivo (testo, contesto, significato, applicazione) e cerca su YouTube le esposizioni/studi biblici pentecostali (ADI, chiese evangeliche) su quel passaggio. |

---

## 📦 Struttura del progetto

```
Assistente-Canzone-TikTok/
├── app.py                 # interfaccia Streamlit (i 4 passaggi)
├── youtube_search.py      # scraping ricerca pubblica YouTube + ranking
├── tiktok_sounds.py       # suoni TikTok (con fallback + link diretti)
├── bible_search.py        # motore di ricerca dei versetti biblici (Riveduta 2020)
├── studio_biblico.py      # riferimenti biblici e i 4 passi dello studio
├── text_tools.py          # grammatica, Salmi, analisi temi, spiegazioni
├── post_generator.py      # caption, hashtag, hook, orari consigliati
├── studio_biblico.py      # riferimenti biblici e i 4 passi dello studio
├── archivio.py            # archivio PRIVATO dei post (un file per utente)
├── ai_client.py           # Google Gemini + IA gratuita (Pollinations)
├── configura.py           # wizard: attiva le chiavi in 2 minuti
├── musica.py              # ACE-Step / MusicGen + creazione del video .mp4
├── suno.py                # Suno (crediti gratuiti) + tag di stile + struttura
├── testi_canzone.py       # l'IA scrive le parole del brano
├── hotreload.py           # ricarica i moduli quando il codice cambia
├── AGGIORNA_COOKIE_SUNO.py # salva/aggiorna il cookie di suno.com in locale
├── AVVIA_SUNO.py          # (facoltativo) servizio open source di Suno
├── pubblica.py            # push con VERSION.txt (commit + deploy)
├── requirements.txt       # dipendenze
├── .streamlit/config.toml # tema e impostazioni
├── AVVIA.ps1              # avvia l'app in locale (PC + telefono)
├── INSTALLA.ps1          # pubblica online con 1 comando (GitHub + Streamlit)
├── INVIA_EMAIL.ps1        # manda l'app via email dal PC
├── email_testo.txt        # testo dell'email
└── link.txt               # (facoltativo) incolla qui il link dell'app
```

---

## 🚀 Pubblicare online con 1 comando (il percorso più veloce)

```powershell
.\INSTALLA.ps1
```

Lo script fa **da solo** tutto quello che può:

1. installa **Git** con winget (se manca);
2. ti chiede solo lo **username GitHub** e il **token** (te apre la pagina
   già pronta: basta spuntare `repo` e cliccare *Generate*);
3. **crea il repository** su GitHub via API;
4. **carica tutto il codice** (il token non resta in nessun file);
5. **apre la pagina di deploy** di Streamlit Cloud già compilata: clicchi
   *Authorize with GitHub* → *Deploy*;
6. **ti manda l'email** con il link definitivo, pronto per il telefono.

L'unica cosa che non può fare al posto tuo è creare l'account GitHub (ci
servono i tuoi dati personali) e autorizzare il tuo account su Streamlit.

Varianti:

```powershell
.\INSTALLA.ps1 -Utente "tuo-username" -Token "ghp_xxxx"
.\INSTALLA.ps1 -NomeRepo "canzoni-tiktok"
```

---

## 🎮 Test in locale sul PC (2 minuti)

Serve Python 3.9+.

```powershell
cd percorso\Assistente-Canzone-TikTok

# 1. ambiente virtuale
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. dipendenze
pip install -r requirements.txt

# 3. avvio
python -m streamlit run app.py
```

Si apre su <http://localhost:8501>. Per vederla dal telefono connesso alla
stessa rete Wi-Fi: `python -m streamlit run app.py --server.address 0.0.0.0`
e apri `http://<IP-del-PC>:8501` dal telefono.

---

## 🆕️ Pubblicare online GRATIS (Streamlit Community Cloud)

Servono ~15 minuti, una volta sola. Da quel momento l'app è raggiungibile da
chiunque, dal telefono, con un link.

### Passo 1 - Crea un account GitHub (gratis)
1. Vai su <https://github.com> e crea l'account.
2. Crea un nuovo repository (es. `canzoni-pentecostali`), **pubblico**.

### Passo 2 - Carica il codice
Dal PC, dentro la cartella del progetto:

```powershell
git init
git add .
git commit -m "Assistente canzoni pentecostali"
git branch -M main
git remote add origin https://github.com/TUO-NOME/canzoni-pentecostali.git
git push -u origin main
```

(Se chiede le credenziali: username GitHub + **Personal Access Token**
incollato come password.)

### Passo 3 - Deploy su Streamlit Cloud
1. Vai su <https://share.streamlit.io> e accedi con GitHub.
2. **New app** -> seleziona il repository `canzoni-pentecostali`,
   branch `main`, file principale `app.py`.
3. Clicca **Deploy**. Dopo 1-2 minuti l'app è online a un indirizzo tipo
   `https://canzoni-pentecostali.streamlit.app`.
4. Copia il link: puoi cambiarlo da **Settings -> URL** in
   `https://canzoni-tiktok.streamlit.app` (piu' semplice da ricordare).

### Passo 4 (facoltativo) - Pulsante "Deploy" nel README
Aggiungi in cima al README:

```markdown
[![Deploy to Streamlit](https://static.streamlit.io/button.svg)](https://share.streamlit.io/deploy?url=https://github.com/TUO-NOME/canzoni-pentecostali)
```

### Nota sul deploy
Lo Streamlit Cloud Community è **gratis** per progetti pubblici e per l'uso
personale. Se il tuo repository e' privato, l'app funziona comunque, ma
potresti dover passare a un piano a pagamento se supera i limiti di risorse.

---

## 📱 Come si usa dal telefono

1. Apri il link dell'app nel browser (Chrome su Android, Safari su iPhone).
2. Menu del browser -> **"Aggiungi alla schermata Home"** (iPhone: pulsante
   Condividi -> "Aggiungi alla schermata Home"). Da quel momento si apre
   come un'app a schermo intero, con la sua icona.
3. Usa l'app esattamente come nel browser.

### 🏠 Usarla subito a casa (senza account)

```powershell
.\AVVIA.ps1
```

Stampa l'indirizzo per il telefono (es. `http://192.168.1.13:8501`): apriolo
nel telefono **stesso Wi-Fi** e usa *Aggiungi alla schermata Home*.
Il PC deve restare acceso.

### 📧 Mandare l'app via email dal PC (con un comando)

Nel PC, dentro la cartella del progetto:

```powershell
# 1) incolla il link dell'app in link.txt (oppure passalo con -Link)
# 2) esegui:
.\INVIA_EMAIL.ps1
```

Lo script:
- legge il link da `link.txt` (o lo chiede a te);
- prepara uno ZIP con tutto il codice;
- **invia l'email con Outlook** (destinatario predefinito
  `enzatoro1@gmail.com`) allegando lo ZIP;
- se Outlook non e' installato, apre il tuo programma email predefinito con
  il messaggio gia' pronto (basta premere Invio).

Varianti:

```powershell
.\INVIA_EMAIL.ps1 -Link "https://canzoni-tiktok.streamlit.app"   # link esplicito
.\INVIA_EMAIL.ps1 -A "altra@email.it"                              # altro destinatario
.\INVIA_EMAIL.ps1 -ApriSolo                                       # non invia, solo prepara
.\INVIA_EMAIL.ps1 -SoloLink                                       # solo link, niente ZIP
```

### 📤 Condividere il link su TikTok
- **In bio**: il link della bio e' cliccabile per tutti -> perfetto per
  scrivere "canzoni per i tuoi video" nel profilo.
- **Nella caption**: TikTok non rende cliccabili i link testuali per tutti
  gli utenti -> meglio rimandare alla bio, oppure condividere il link
  come messaggio privato.
- **Email / WhatsApp**: il modo piu' semplice per gli amici e la famiglia.

---

## 🧪 Come funziona (tecnica)

### La ricerca (il "cervello")
1. `estrai_parole_chiave()` toglie le stopword italiane/inglesi e privilegia
   il lessico religioso -> restano 3 parole chiave.
2. `costruisci_query()` le unisce al suffisso di genere scelto
   ("musica evangelica pentecostale lode", "inno pentecostale", ...).
3. `cerca_youtube()` scarica la pagina pubblica di ricerca YouTube, estrae
   il blocco JSON `ytInitialData` e ne legge i `videoRenderer`
   (titolo, canale, durata, link).
4. `ricerca_multiplica()` esegue 2-3 query, elimina i duplicati e ordina per
   punteggio (parole chiave nel titolo, genere, durata adatta a un video
   corto).
5. Se un giorno YouTube cambiasse formato, interviene il metodo di riserva
   `yt-dlp` (in `requirements.txt`).

### Il motore dei versetti ("Trova il testo adatto")
1. Il tuo pensiero viene scomposto in **concetti** (le parole che non sono
   stopword).
2. Ogni concetto viene tradotto nelle sue **radici bibliche equivalenti**
   ("perdonami" -> perdona, rimette, misericordia; "paura" -> timore, terrore...).
3. I versetti vengono cercati per ogni concetto e messi in classifica: un
   versetto che contiene **due concetti diversi** vince su uno che ne
   contiene uno solo (per questo "perdonami perche' ho peccato" porta a
   Salmi 32,1 e non alle liste di offerte del Levitico).
4. Il corpus e' la **Sacra Bibbia - Versione Riveduta 2020**, traduzione
   protestante/evangelica (non cattolica), scaricata una volta e messa in
   cache.

### Perche' la ricerca audio di TikTok non e' diretta
La libreria audio di TikTok e' protetta: i suoi endpoint interni richiedono
una firma anti-bot del dispositivo (`X-Bogus` / `X-Gorgon`) e rispondono con
corpo vuoto se manca. Per questo l'app:
- tenta comunque gli endpoint pubblici a ogni ricerca (se TikTok li
  riapre, l'app li usa da sola);
- e soprattutto porta con un tocco alla **ricerca suoni di TikTok** gia'
  impostata sul titolo esatto della canzone (funziona nel browser del
  telefono, anche dentro l'app TikTok).

### Perche' non si puo' pubblicare in automatico
La pubblicazione automatica richiede la **Content Posting API** di TikTok,
che prevede account sviluppatore, registrazione di un'app e approvazione
ufficiale (mesi di iterazione). L'app quindi prepara tutto il materiale e ti
distingue 3 tocchi: copia la caption -> apri TikTok -> incolla e pubblica.

---

## 🔧 Personalizzazione

| Cosa | Dove |
|------|-------|
| Tema colori | `.streamlit/config.toml` (`primaryColor`, ecc.) |
| Suffissi di ricerca | `youtube_search.py` -> dizionario `STILI` |
| Parole "religioushe" prioritarie | `youtube_search.py` -> `TERMINE_RELIGIOSI` |
| Temi dell'analisi | `text_tools.py` -> dizionario `TEMI` |
| Formati di caption | `post_generator.py` -> `FORMATI_POST` + dizionario `APERTURE`/`CHIUSURE` |
| Orari consigliati | `post_generator.py` -> `suggerisci_orari()` |
| Salmi riconosciuti | `text_tools.py` -> `SALMI_NOTI` |
| Libri biblici riconosciuti | `studio_biblico.py` -> `LIBRI` |

---

## 🐛 FAQ

**L'app funziona senza internet?**
No: servono YouTube (per la ricerca) e LanguageTool (per la grammatica).
Senza rete l'app non si blocca: mostra un avviso e usa le correzioni locali.

**Devo avere un account TikTok per usarla?**
No. Serve solo per pubblicare (e lo fai dall'app TikTok).

**TikTok ha cambiato qualcosa?**
L'app non dipende da dati interni di TikTok: se i link di ricerca audio
cambiano, basta aggiornare `tiktok_sounds.py`.

**Posso usarla per altri temi (non cristiani)??**
Si': in `youtube_search.py` cambia i suffissi in `STILI` e in
`TERMINE_RELIGIOSI`; il resto funziona uguale.

**L'archivio si perde?**
Su Streamlit Cloud il file dell'archivio vive nel container: resta per la
sessione del servizio. Se il filesystem non e' scrivibile, l'app comunque
continua a funzionare (l'archivio resta in memoria).

## 🖥️ Se scarichi l'app e la fai girare sul tuo computer

```bash
pip install -r requirements.txt
python -m streamlit run app.py
```
→ http://localhost:8501

**Per attivare Gemini** (facoltativo, gratis): crea il file
`.streamlit/secrets.toml` **nella cartella del progetto** con:

```toml
GEMINI_API_KEY = "la-tua-chiave-di-Google-AI-Studio"
```

(il file è già in `.gitignore`: la chiave **non** finisce su GitHub)

Oppure, senza toccare i file: incolla la chiave nella barra laterale
dell'app, campo "Chiave Google Gemini", e spunta
**"Ricorda la chiave su QUESTO dispositivo"** (resta nel tuo browser,
solo tua, la quota non la consuma nessun altro).

**Su Streamlit Cloud** la chiave si mette nei *Secrets*
(share.streamlit.io → la tua app → ⋮ → Settings → Secrets → `GEMINI_API_KEY`).
Attenzione: i Secrets sono condivisi da tutti gli utenti dell'app, quindi la
quota gratuita è di tutti. Se l'app è solo tua, meglio la chiave nel browser.

---

**Ogni persona che usa l'app vede solo i propri post.**

- Ogni utente ha un **identificatore automatico** (un cookie `cantico_uid`
  nel suo browser): **non deve scrivere nessun codice**.
- L'id NON viene salvato in chiaro: viene trasformato in un hash SHA-256
  che da' il nome al file (`archivio_<hash>.json`). Dal nome del file non si
  ricava l'id.
- **Tu non vedi i post degli altri** e **gli altri non vedono i tuoi**.
- Se vuoi cancellare tutto, c'è il pulsante **"Cancella i miei dati"**.

Cosa NON viene condiviso con nessuno ( resta nel browser dell'utente ):
- il testo che scrivi, i versetti cercati, le interpretazioni
- la cronologia delle ricerche
- la chiave API OpenAI (se la digiti tu)

Unica cosa condivisa: la **cache dei risultati di ricerca** (stesse
query -> stesse risposte, per non interrogare YouTube due volte) e la
**cache della Bibbia** (il testo sacro, che e' pubblico).

---

## 🎵 La canzone ORIGINALE (canta il tuo versetto) + il video TikTok

Nella sezione **"Crea una canzone ORIGINALE"** (in fondo al PASSAGGIO 3):

1. **L'IA scrive il testo** del brano (come un songwriter di lode) — puoi
   correggerlo a mano
2. **Il motore musicale lo canta** (1-3 minuti, può mettersi in coda)
3. **L'app crea il video .mp4** verticale 9:16, con sfondo a scelta:
   - *immagine* → gradiente con il testo del verso
   - *nero* → tela nera con la scritta
   - *foto* → una tua immagine
   - *loop animato* → leggero zoom (come un video)

### I motori musicali (tutti con i tag di stile che hai chiesto)

| Motore | Cosa serve | Costo |
|---|---|---|
| **Treblo** (canta il testo, audio scaricabile) | una chiave API Treblo | **gratis** (3.000 crediti = 30 canzoni) |
| **Suno (i tuoi crediti gratuiti)** | solo il tuo cookie di suno.com (niente da installare) | **gratis** (i crediti giornalieri del tuo account) |
| **ACE-Step** (open source, canta il testo) | un token Hugging Face gratis per la quota GPU | gratis |
| **MusicGen** (open source, strumentale) | un token Hugging Face gratis | gratis |
| **Il tuo brano** | niente: carichi il file audio e l'app fa il video | gratis |

> **Attenzione, una cosa che cambia spesso:** Suno (dal 2026) **cifra
> l'audio** che scarica: il brano si genera e si ascolta nella tua libreria
> su suno.com, ma il file non si puo' salvare in automatico. Per questo
> l'app ti lascia **caricare qui il brano** (che scarichi da suno.com con
> un tocco) e ci fa sopra il video. Se preferisci che sia tutto automatico,
> usa **ACE-Step** con un token Hugging Face gratis: l'audio e' open source
> e l'app lo scarica e lo monta da sola.

> **Solo motori gratuiti.** Nell'app non c'e' nessun motore a pagamento e
> nessuna chiave da ricaricare: chi riceve l'app non deve creare nulla,
> funziona subito. Se un motore non risponde, l'app passa al successivo e
> alla fine spiega cosa manca.

**Tag di stile sempre applicati** (in `suno.py`):
- stile: *Modern Christian Worship, contemporary gospel, inspiring,
  uplifting, powerful vocal harmony, emotional, Christian Worship, Gospel,
  Italian vocal*
- strumenti: *Acoustic guitar, ambient piano, cinematic synths, build-up
  drums, emotional strings*

**Struttura del brano**: il testo viene diviso automaticamente in
`[Verse]` e `[Chorus]` (le tag restano se ci sono già).

### Come si usa Treblo (il motore che canta e ti fa il video da solo)

Treblo (ex Sonauto) ha un'API pubblica e 3.000 crediti gratis al primo
accesso. E' il motore piu' comodo: **canta** le parole del brano e ti lascia
**scaricare l'audio**, cosi' il video .mp4 si fa tutto da solo.

1. Crea l'account su <https://treblo.com> (Google va bene).
2. Crea la chiave API su <https://treblo.com/developers/account>.
3. Incollala nell'app, nella barra laterale, campo **"Chiave Treblo"**.
4. Nell'app: motore **"Treblo (crediti gratis, canta il testo)"** →
   "Componi e canta la canzone" → "Fai il video per TikTok".

Ogni canzone costa 100 crediti → con i 3.000 gratis fai **30 canzoni**.
La chiave resta nel tuo browser (campo password): non finisce su GitHub.
I crediti gratis si sbloccano verificando una carta (non viene addebitato
nulla); dopo si puo' continuare a consumo o con un piano.

> *Attribuzione: Treblo chiede che chi usa la sua API ne citi il nome.
> L'app lo fa nella sezione "Crea una canzone ORIGINALE".*

### E se non vuoi registrarti da nessuna parte?

**Vidnoz AI Music Generator** (<https://www.vidnoz.com/ai-music.html>) è
gratis, **senza registrazione e senza carta**: scegli la modalità
*"Canzone con testo"*, incolli le parole del brano, scegli il genere e la
voce (maschile/femminile) e scarichi il MP3 (royalty-free, uso commerciale
consentito anche nella versione gratis).

In quel caso: scarica il brano da Vidnoz e **caricalo qui** nella sezione
"Crea una canzone ORIGINALE" → riquadro **"🎧 Carica il brano"**: l'app ci
fa sopra il video .mp4 verticale.

### Come si usa Suno con i crediti gratuiti (una volta sola)

Suno non ha un'API pubblica per gli account gratuiti, ma la sua app web parla
con un'API interna. L'app fa esattamente quello: **non devi installare
niente** (niente Node.js, niente servizi, niente account).

1. **Fai il login su <https://suno.com>** con il tuo account.
2. **Copia il cookie** (senza passarlo dalla chat):
   - F12 → scheda **Network** (Rete) → ricarica la pagina (F5) → clicca una
     richiesta → in **Request Headers** copia la riga **cookie**;
   - salvalo sul tuo computer:
     ```powershell
     python AGGIORNA_COOKIE_SUNO.py
     ```
     e incolla il valore. Finisce nel file `.suno_cookie.txt`, che è in
     `.gitignore`: il cookie **non** finisce su GitHub.
3. Nell'app: motore **"Suno (i tuoi crediti gratuiti)"** → "Componi e canta".

> **Il cookie vale circa un'ora** (è una sessione di browser). Quando
> scade l'app lo dice e basta rinnovarlo. Ci sono due modi, entrambi senza
> passare dalla chat:
>
> - ** Dentro l'app** (più comodo): apri la barra laterale → *"Suno: i crediti
>   gratuiti del TUO account"* → incolla il nuovo cookie → **"Attiva subito
>   (per me)"** → **"Verifica i crediti"** per essere sicuro.
> - **Dal terminale**: `python AGGIORNA_COOKIE_SUNO.py` (scrive il file
>   `.suno_cookie.txt`).
>
> Se preferisci la via "servizio open source" (Node.js sulla porta 8000),
> c'è anche quella: `python AVVIA_SUNO.py`. L'app la usa solo come riserva.
>
> **Il token Hugging Face** (per ACE-Step e MusicGen) è gratis:
> <https://huggingface.co/settings/tokens> → *New token* → *Read* → incollalo
> nel campo "Token Hugging Face" della barra laterale. Serve a far partire
> i modelli open source (senza token la quota GPU pubblica è esaurita).

## 🧩 Per chi scarica l'app: come si attiva tutto (2 minuti)

L'app **funziona subito anche senza chiavi** (motore di studio + IA
gratuita + video). Ma per avere l'interpretazione da "maestro della
Scrittura" e la canzone cantata, servono due chiavi: **le crea e le
incolla chi usa l'app**, dentro l'app stessa.

**La finestra dentro l'app**: apri la barra laterale → se non hai ancora
niente, compare **"🧩 Attiva tutto (2 minuti)"** con i passi esatti:

1. **Google Gemini** → https://aistudio.google.com/api-keys
   → "Create API key" → incolla qui → **"Attiva subito (per me)"**
   *La chiave è attiva subito, anche sull'app online.*
2. **Suno** (facoltativo, per la canzone cantata con i tuoi crediti
   gratuiti) → le istruzioni sono nella stessa finestra

> Tutto il resto (versetti, interpretazione, ricerca delle canzoni, video
> .mp4) funziona **senza toccare nulla**: la chiave serve solo per
> l'interpretazione più profonda e per la musica.

**Dove finiscono le chiavi** (scelte del wizard):
- **"Attiva subito (per me)"** → valgono solo nella tua sessione
- **"Salva sul computer"** → nel file `.streamlit/secrets.toml` (locale,
  **in `.gitignore`**: non finiscono MAI su GitHub)
- **"Condividi con tutti"** → sul server: la quota diventa di tutti

> Nessun'altra persona (ne' io, ne' il server) vede le chiavi di chi le
> ha inserite. Io scrivo il codice che le collega, ma **la chiave la
> incolla sempre chi la possiede**.

---

## ❤️ Fatto per i creator cristiani

---

## ✍️ "Mia riflessione": scrivi, l'app trova il verso giusto

La terza scheda dell'app serve a questo: ogni giorno, quando leggi la
Bibbia, annoti **con parole tue** quello che ti ha parlato.

1. Apri la scheda **"📝 Mia riflessione"**
2. Scrivi il tuo pensiero (es. *"Dio non abbandona nessuno: anche quando
   mi sento solo, lui c'è"*)
3. Tocca **"Trova il versetto e la canzone"**

Cosa succede:
- l'app **cerca in tutta la Bibbia** (66 libri) i versetti che parlano al
  tuo pensiero
- **l'IA sceglie il versetto giusto** (non quello con parole simili ma
  senso opposto) e lo mette in cima con il badge "🌟 scelto dall'IA" e la
  spiegazione del perché
- scegli il versetto → l'app cerca **la canzone** e prepara il post
- la **caption parte dalle tue parole**, non dal versetto: la tua riflessione
  è il cuore del post, il versetto è il riferimento

La scelta dell'IA può indicare anche un versetto **che non era tra i
candidati** (l'app lo cerca nella Bibbia e lo usa). Esempi reali:

| La tua riflessione | Il versetto scelto dall'IA |
|---|---|
| "Dio non abbandona nessuno" | Ebrei 13,5 |
| "Il perdono libera prima chi lo chiede" | Matteo 6,14-15 |
| "Ho paura del futuro ma so che Dio provvede" | Salmi 56,3 |

C'è anche **"📖 Pubblica la riflessione di oggi"**: salva la riflessione
come post pronto (con data), per quando vuoi pubblicarla subito.

---

## 🔎 Il doppio passaggio (versetto -> interpretazione -> canzone)

Quando scrivi un **Salmo o un versetto** (es. `Salmo 23:1`), l'app lavora in due fasi:

**FASE 1 - Interpretazione dottrinale pentecostale**
1. Riconosce il riferimento e porta il **testo integrale** del versetto dalla
   Sacra Bibbia - Versione Riveduta 2020 (canon protestante, 66 libri), con i
   versetti di contesto.
2. Cerca su YouTube le **esposizioni, gli studi e le prediche** di chiese
   evangeliche/pentecostali su quel passaggio.
3. Scarica la **trascrizione** della predicazione (solo se parla davvero del
   versetto) e la usa come interpretazione; in alternativa genera
   l'interpretazione di studio secondo la dottrina evangelica pentecostale.
4. Estrae le **3 parole chiave spirituali** (es. *fiducia, luce, pastore*).

### 🎯 L'interpretazione è sempre diversa da versetto a versetto

Il motore di studio **non** ripete lo stesso testo: guarda le **immagini reali**
del versetto (pietra, via, vite, pane, luce, pastore...) e costruisce
l'analisi su quelle. Esempio:

| Versetto | Cosa dice l'interpretazione |
|---|---|
| Giovanni 14,6 | "una promessa che parla di **via, verità e vita**" |
| Marco 12,10 | "una promessa che parla di **pietra**" |
| Salmo 23,1 | "una promessa che parla di **pastore**" |

### 🆓 L'app funziona bene anche SENZA la chiave (per chi la scarica)

Se qualcuno scarica il codice e lo usa per conto proprio, **non ha la
chiave Gemini**: l'app deve comunque essere buona. E lo è:

1. **Motore di studio** (sempre disponibile): costruisce l'interpretazione
   **sul versetto** — riconosce le sue **immagini** (pietra, vite, pastore,
   luce, tempio, mare…) e scrive il significato, il contesto e la lode
   partendo da quelle. Ogni versetto ha un testo **diverso**.
2. **IA gratuita senza chiave** (Pollinations): ci prova sopra, con 3 tentativi
   e attesa, e scarta le risposte non utilizzabili.
3. Se entrambe falliscono, l'app **non si blocca**: mostra lo studio del
   versetto e un avviso chiaro su come attivare Gemini.

Nella barra laterale c'è anche la spiegazione per chi scarica l'app:
*"Senza chiave l'app funziona lo stesso… ma con una chiave Gemini gratuita
l'interpretazione diventa molto più profonda"*.

La chiave si può salvare in **due modi**, e la scelta è tua:

| Dove | Chi la usa | Quota |
|---|---|---|
| **"Ricorda su QUESTO dispositivo"** (default) | solo te, nel tuo browser | **solo tua** ✅ |
| "Condividi con TUTTI gli utenti" | chiunque usi l'app | **condivisa** ⚠️ |
| Secrets di Streamlit Cloud | chiunque usi l'app | **condivisa** ⚠️ |

---

Nella sezione **"Da dove vuoi l'interpretazione?"** c'è il pulsante
**🧠 Scrivi l'interpretazione con l'IA**. Funziona **anche senza toccare
nulla**: l'app sceglie da sola l'IA migliore disponibile, in quest'ordine:

| Ordine | IA | Serve la chiave? | Qualità |
|---|---|---|---|
| 1° | **Google Gemini** (`gemini-2.0-flash`) | sì, **gratis** | ⭐⭐⭐⭐⭐ |
| 2° | IA gratuita senza chiave (Pollinations) | no | ⭐⭐⭐ |
| 3° | ChatGPT API | sì (OpenAI) | ⭐⭐⭐⭐⭐ |

**Come si prende la chiave Gemini (gratis, 1 minuto)**
1. Apri <https://aistudio.google.com/api-keys> con il tuo account Google
2. "Crea chiave API" → copiala
3. **Per l'app online** (vale per tutti): mettila nei *Secrets* di
   Streamlit Cloud
   - apri <https://share.streamlit.io> → la tua app → **⋮ → Settings →
     Secrets**
   - scrivi `GEMINI_API_KEY = "la-tua-chiave"` → **Save**
   - l'app si riavvia da sola e la barra laterale mostra
     "✅ Gemini è già attivo"
4. **Per l'app sul PC**: la chiave va in
   `.streamlit/secrets.toml` (questo file è in `.gitignore`, **mai** su
   GitHub):
   ```toml
   GEMINI_API_KEY = "la-tua-chiave"
   ```

In alternativa si può incollare la chiave ogni volta nella barra laterale
dell'app (campo "Chiave Google Gemini").

**Opzione comoda: "Ricorda su QUESTO dispositivo" (solo per te)**
Nella barra laterale, sotto il campo della chiave, ci sono due spunte:

1. **"Ricorda la chiave su QUESTO dispositivo (solo per me)"** ← consigliata
   La chiave viene salvata nel **tuo browser** (come una password salvata):
   - non la reinserisci più
   - **nessun altro utente la vede** e **la quota resta tua**
   - non finisce né su GitHub né sul server
2. "Condividi la chiave con TUTTI gli utenti dell'app"
   La chiave viene salvata nel container (`.chiave_gemini_server.json`,
   **in `.gitignore`**): vale per tutti, ma la **quota è condivisa**.

> Nota: su Streamlit Cloud il filesystem del container viene azzerato a ogni
> nuovo deploy, quindi dopo un aggiornamento dell'app la chiave ricordata
> sparisce e va reinserita una volta (o rimessa nei Secrets).

L'app usa la **SDK ufficiale `google-genai`** (la stessa del tuo esempio:
`from google import genai` → `genai.Client()` → `client.models.generate_content(...)`)
e, se il pacchetto non è installato, ripiega su una chiamata HTTP diretta.
Prova i modelli in ordine (`gemini-3.8-flash`, `gemini-flash-latest`,
`gemini-2.5-flash`, `gemini-3.5-flash`, `gemini-flash-lite-latest`) e usa
il primo che risponde, così non si blocca quando Google è sotto carico.

**L'IA scrive come un maestro della Scrittura**: 5 sezioni (Il testo, Il
contesto, Il significato, Dalla voce di Dio al nostro cuore, Per la lode),
con regole esplicite nel prompt:
- parte **sempre e solo** dal testo del tuo versetto
- usa i nomi **esattamente** come sono nel testo (niente allucinazioni)
- non cita altri passaggi di cui non è sicuro
- non cita canzoni (le cerca l'app)

**Controllo qualità**: se la risposta dell'IA è "rotta" (italiano sbagliato,
ripetizioni, oppure solo il **ragionamento** del modello invece della
risposta) l'app **la scarta** e prova il servizio successivo; se falliscono
tutti, usa il motore di studio del versetto. Non vedrai mai una pagina di
nonsenso né un ragionamento in inglese.

> Nota tecnica: l'IA gratuita senza chiave usa un modello piccolo che
> "ragiona" prima di rispondere. Per questo l'app gli manda un'istruzione
> **breve** e poi verifica che la risposta sia in italiano e contenga le
> sezioni richieste; con Google Gemini (che è molto più bravo) la
> qualità è di un altro livello.

**Le parole chiave collegano IA e canzoni**: l'IA scrive alla fine
`Parole chiave: Fede, Speranza, Amore`, e sono **quelle** che l'app usa per
cercare la canzone. Quindi la canzone proposta parla davvero
dell'interpretazione.

C'è anche **🔄 Riscrivi** (un'altra versione della stessa interpretazione)
accanto al pulsante "Copia".

Le altre due opzioni restano: **"Chiedi a ChatGPT"** (copia il prompt e
apre ChatGPT) e **"Interpreta con ChatGPT"** (la tua chiave API OpenAI).

**FASE 2 - Ricerca musicale forzata**
```
[Salmo 23] + [fiducia luce pastore]
  + "musica cristiana evangelica pentecostale lodi ADI cantico evangelico"
  + [-cattolica -cattolico -messa -mondana -pop -remix -gregoriano -mariano]
```

### 🎵 La ricerca delle canzoni: multilingue e "collezioni fidate"

La ricerca non guarda solo in italiano: l'app costruisce **query in italiano,
inglese e spagnolo**, traducendo anche il riferimento biblico
(`Giovanni 14,6` → `John 14:6` / `Juan 14:6`).

**Le collezioni fidate**: per ogni lingua l'app fa una ricerca dedicata su
artisti e canali di lode che pubblicano brani moderni (quelli che su TikTok
funzionano davvero):

| Lingua | Collezioni |
|---|---|
| Italiano | Activate Music, MUSICA CRISTIANA ITALIANA, Praised Voices, Officine Meccaniche… |
| Inglese | Elevation Worship, Hillsong, Bethel Music, Maverick City, Planetshakers… |
| Spagnolo | Adoracion Celestial, Energia Positiva con Amor, Chris Adan, Miel Sv… |

**I video ufficiali non sono più penalizzati**: i canali "Artista - Topic" e
i "(Official Videoclip)" sono la versione *vera* del brano, quella che si
trova nella libreria audio di TikTok. Ricevono un bonus e il **badge
"artista"** sulla scheda.

**Copia "Titolo - Artista"**: il pulsante "Copia Titolo" copia il formato
che funziona su TikTok (es. `Power - Elevation Worship`), e anche il link
"Verifica l'audio su TikTok" usa quel formato.

**Più canzoni**: la ricerca restituisce **15 brani** (prima erano 5) e
"Cerca meglio" ne porta **8 altri** ogni volta, tutti diversi. C'è un limite
di 4 brani per canale, così la lista resta varia.

| Regola | Come funziona |
|--------|---------------|
| **Solo musica evangelica** | I contenuti cattolici (liturgia, mariani, santuari, catechismo) vengono **scartati in Python**, oltre alle keyword negative |
| **Localizzazione** | YouTube viene interrogato con `hl=it` e `gl=IT` ( Italiano, area Italia) |
| **Mood automatico** | Se il testo parla di ravvedimento/consolazione -> "adorazione profonda", "musica per preghiera"; se parla di vittoria/gioia -> "lode movimentata", "coro pentecostale", "inni di vittoria" |
| **Durata** | Scartati i video oltre 7 minuti (compilazioni, culti registrati); preferiti i brani singoli di 3-5 minuti |
| **Testo pulito** | Tolte note `[a]`, numeri in apice, simboli e formattazioni delle Bibbie online |
| **Priorità al capitolo** | Riconosciuto "Salmo 23" o "Giovanni 3" e la ricerca parte da quel riferimento |
| **Fallback** | Se la query stretta non dà risultati, l'app riprova con la query allargata (il filtro cattolico resta attivo) |
| **Doppio controllo** | Prima la query esatta, poi la più larga: il risultato migliore vince |

Il prompt per l'interpretazione (per chi vuole usare ChatGPT) si trova
nell'app, sotto "Il prompt per l'interpretazione".
