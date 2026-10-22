# AGENTS.md - regole di lavoro per questo progetto (CANTICO)

Utente: **Enzo**, italiano, non programmatore. Comunica in italiano, tono
pratico, niente gergo tecnico. Le risposte devono essere brevi e operative.

---

## 1. Il browser condiviso: come non bloccarsi

Il browser è **condiviso con l'utente**: se lui muove il mouse, cambia
scheda o scrolla, le chiamate al browser vengono **annullate**
("Tool execution interrupted"). È un limite dello strumento, non un freeze.

**Regole ferree:**

1. **Una sola azione per chiamata.** Non mescolare "apri + attendi + clicca
   + leggi" in un unico blocco: se viene annullato, si perde tutto.
2. **Mai attese lunghe dentro la stessa chiamata.** Attendi al massimo
   ~8 secondi per chiamata; per il resto, richiama l'attesa in una chiamata
   separata.
3. **Prima di ogni operazione**, fai `browser.tabs.list` e usa l'id
   esatto della scheda giusta: gli `ref` e i `tabID` scadono quickly.
4. **Non aprire schede duplicate** sulla stessa URL: riusa quella che c'è.
5. **Se una chiamata viene annullata**: non ripetere lo stesso blocco.
   Semplifica (solo lettura, niente click) oppure **chiedi una schermata
   all'utente** invece di insistere col browser.
6. **Il browser è l'ultima risorsa** per verificare qualcosa. Prima controlla
   con `git`, `grep`, un test locale. Usa il browser solo per cose che
   non si vedono da fuori (il rendering finale).
7. **Timeout mentali**: se non funziona in 2 tentativi, cambia metodo e
   dillo all'utente in modo chiaro, senza girarci intorno.

---

## 2. Progetto: fatti che non vanno dimenticati

- App **Streamlit** (`app.py`) per creator cristiani: versetto -> canzone
  -> post TikTok.
- **Deploy**: `python pubblica.py "messaggio"` = commit + `VERSION.txt` +
  push su `origin/main`. Streamlit Cloud fa il redeploy da solo (1-2 min).
- **Versione**: l'app mostra `build <sha>`; se l'utente ha la pagina
  aperta da prima, deve premere **"Ricarica la versione piu' recente"**.
- **Moduli nuovi** (`riflessione`, `setup_app`, `tiktok_pubblica`) devono
  stare nella lista `ORDINE` di `hotreload.py`: senza, il server tiene in
  memoria la versione vecchia e l'app si rompe con un `AttributeError`.
- **Le chiavi non viaggiano mai su GitHub**: `.streamlit/secrets.toml`,
  `SEGRETS-CLOUD.txt`, `TIKTOK-CHIAVI.txt` e `archivio_*.json` (dati
  personali) sono in `.gitignore` e vanno esclusi anche dallo ZIP che si
  manda via email (`INVIA_EMAIL.ps1`).
- **Ogni utente mette le SUE chiavi** (nel browser): la quota resta sua.
  Il proprietario non paga per gli altri.
- **La copia distribuita** (`prepara_distribuzione.py`) non ha password:
  chi la apre la imposta e si configura da solo.

---

## 3. Prima di scrivere codice

- Il progetto ha uno **stile**: italiano nei commenti e nei messaggi
  dell'app, codice semplice, niente dipendenze nuove se evitabili.
- Verifica sempre con `python -m py_compile` e, se tocchi la logica,
  con un test offline (senza rete).
- Non rifare le modifiche a tentativi: trova la causa una volta sola.
