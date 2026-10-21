# -*- coding: utf-8 -*-
"""
AVVIA IL SERVIZIO SUNO (open source) con i TUOI crediti gratuiti
===============================================================
Questo script avvia il ponte open source verso suno.com, usando la
sessione del TUO account (quindi i crediti gratuiti giornalieri).

COME SI USA (dal PC o dal Codespace):
    python AVVIA_SUNO.py

Lo script:
    1) controlla che ci sia il cookie (.suno_cookie.txt)
    2) scarica il progetto open source (se non c'e') FUORI da OneDrive
    3) installa le dipendenze (npm install)
    4) applica la "riserva" sul cookie __session (per non dover copiare
       anche il cookie httpOnly __client)
    5) lancia il servizio e verifica che l'API risponda su
       http://localhost:8000
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")

PROG = os.path.dirname(os.path.abspath(__file__))
REPO_SUNO = "https://github.com/gcui-art/suno-api"
# il servizio va FUORI da OneDrive (lì node_modules si rompe)
CARTELLA = os.path.join(os.path.expanduser("~"), "suno-api")
FILE_COOKIE = os.path.join(PROG, ".suno_cookie.txt")
PORTA = 8000

# la "riserva": se il cookie httpOnly __client non c'e', il servizio usa
# il cookie __session (che e' un JWT con dentro l'id della sessione)
PATCH = """  private async getAuthToken() {
    logger.info('Getting the session ID');
    // URL to get session ID
    const getSessionUrl = `${SunoApi.CLERK_BASE_URL}/v1/client?__clerk_api_version=2025-11-10&_clerk_js_version=${SunoApi.CLERK_VERSION}`;
    try {
      // Get session ID
      const sessionResponse = await this.client.get(getSessionUrl, {
        headers: { Authorization: this.cookies.__client }
      });
      if (sessionResponse?.data?.response?.last_active_session_id) {
        // Save session ID for later use
        this.sid = sessionResponse.data.response.last_active_session_id;
        return;
      }
    } catch (e) {
      logger.warn('Session lookup failed, falling back to the __session cookie');
    }
    // RISERVA: il cookie __session e' un JWT che contiene gia' l'id della
    // sessione (sid) e il token da usare come Bearer.
    const dalCookie = this._dalCookieSessione();
    if (!dalCookie) {
      throw new Error(
        'Failed to get session id, you may need to update the SUNO_COOKIE'
      );
    }
    this.sid = dalCookie.sid;
    this.currentToken = dalCookie.token;
    logger.info(`Session ID taken from the __session cookie: ${this.sid}`);
  }

  /**
   * Legge il cookie __session (JWT) e ricava l'id della sessione + il token.
   */
  private _dalCookieSessione(): { token: string; sid: string } | null {
    const grezzoCookie = this.cookies.__session;
    if (!grezzoCookie) {
      return null;
    }
    try {
      const parte = grezzoCookie.split('.')[1];
      const dati = JSON.parse(Buffer.from(parte, 'base64url').toString('utf-8'));
      if (dati && dati.sid) {
        return { token: grezzoCookie, sid: String(dati.sid) };
      }
    } catch (e) {
      logger.warn('The __session cookie is not a readable JWT');
    }
    return null;
  }"""


def _servizio_vivo() -> bool:
    """Il servizio risponde e l'account e' collegato?"""
    try:
        import requests
        r = requests.get(f"http://localhost:{PORTA}/api/get_limit", timeout=20)
        if r.status_code != 200:
            return False
        dati = r.json()
        crediti = dati.get("credits_left")
        print(f"      crediti gratuiti rimasti: {crediti}")
        return True
    except Exception:
        return False


def _applica_patch() -> None:
    """Rende il servizio robusto quando manca il cookie httpOnly __client."""
    sorgente = os.path.join(CARTELLA, "src", "lib", "SunoApi.ts")
    if not os.path.exists(sorgente):
        return
    try:
        with open(sorgente, "r", encoding="utf-8") as f:
            testo = f.read()
    except Exception:
        return
    if "_dalCookieSessione" in testo:
        print("      la riserva sul cookie __session e' gia' presente.")
        return
    vecchio = """  private async getAuthToken() {
    logger.info('Getting the session ID');
    // URL to get session ID
    const getSessionUrl = `${SunoApi.CLERK_BASE_URL}/v1/client?__clerk_api_version=2025-11-10&_clerk_js_version=${SunoApi.CLERK_VERSION}`;
    // Get session ID
    const sessionResponse = await this.client.get(getSessionUrl, {
      headers: { Authorization: this.cookies.__client }
    });
    if (!sessionResponse?.data?.response?.last_active_session_id) {
      throw new Error(
        'Failed to get session id, you may need to update the SUNO_COOKIE'
      );
    }
    // Save session ID for later use
    this.sid = sessionResponse.data.response.last_active_session_id;
  }"""
    if vecchio not in testo:
        print("      (il codice del servizio e' cambiato: salto la riserva)")
        return
    testo = testo.replace(vecchio, PATCH)
    try:
        with open(sorgente, "w", encoding="utf-8", newline="\n") as f:
            f.write(testo)
        print("      applicata la riserva sul cookie __session.")
    except Exception as exc:
        print(f"      non sono riuscito a applicare la riserva: {exc}")


def main() -> int:
    print("=" * 70)
    print("SERVIZIO SUNO (crediti gratuiti del tuo account)")
    print("=" * 70)

    if _servizio_vivo():
        print(f"\nIl servizio e' GIA' attivo su http://localhost:{PORTA}.")
        print("Vai nell'app -> 'Crea una canzone ORIGINALE' -> motore Suno.")
        return 0

    # 1) il cookie
    if not os.path.exists(FILE_COOKIE):
        print("\n[1/5] Non trovo il cookie di suno.com.")
        print("      Fai il login su https://suno.com, poi:")
        print("      F12 -> Network -> ricarica (F5) -> clicca una richiesta")
        print("      -> Request Headers -> riga 'cookie' -> copia il valore")
        print("      e poi lancia:  python AGGIORNA_COOKIE_SUNO.py")
        return 1
    print("\n[1/5] Cookie trovato.")

    # 2) il progetto
    if not os.path.isdir(CARTELLA):
        print("[2/5] Scarico il progetto open source...")
        try:
            subprocess.run(["git", "clone", "--depth", "1", REPO_SUNO, CARTELLA],
                           check=True, timeout=300)
        except Exception as exc:
            print(f"      ERRORE: {exc}")
            return 1
    else:
        print("[2/5] Progetto gia' presente.")

    # 3) npm install
    npm = shutil.which("npm")
    if not npm:
        print("\n[3/5] 'npm' non trovato: installa Node.js (nodejs.org) "
              "e riprova.")
        return 1
    if not os.path.exists(os.path.join(CARTELLA, "node_modules", "next")):
        print("[3/5] Installo le dipendenze (npm install)...")
        try:
            subprocess.run([npm, "install"], cwd=CARTELLA, check=True,
                           timeout=900)
        except Exception as exc:
            print(f"      ERRORE in npm install: {exc}")
            return 1
    else:
        print("[3/5] Dipendenze gia' installate.")

    # 4) la riserva sul cookie
    print("[4/5] Preparo il servizio...")
    _applica_patch()
    try:
        with open(FILE_COOKIE, encoding="utf-8") as f:
            cookie = f.read().strip()
        with open(os.path.join(CARTELLA, ".env"), "w", encoding="utf-8",
                  newline="\n") as f:
            f.write(f"SUNO_COOKIE={cookie}\n")
            f.write("BROWSER=chromium\nBROWSER_HEADLESS=true\n"
                    "BROWSER_LOCALE=en\n")
    except Exception as exc:
        print(f"      ATTENZIONE: non sono riuscito a preparare il .env: {exc}")

    # 5) avvio
    print(f"[5/5] Avvio il servizio su http://localhost:{PORTA} ...")
    print("      (lascia questa finestra APERTA: il servizio deve restare vivo)")
    env = dict(os.environ)
    env["PORT"] = str(PORTA)
    env.setdefault("SUNO_COOKIE", cookie)
    try:
        proc = subprocess.Popen([npm, "run", "dev"], cwd=CARTELLA, env=env)
    except Exception as exc:
        print(f"      ERRORE: {exc}")
        return 1

    print("      Aspetto che l'API risponda...")
    for _ in range(60):
        time.sleep(3)
        if _servizio_vivo():
            print("\n      FATTO! L'API e' attiva su "
                  f"http://localhost:{PORTA}")
            print("      Ora apri l'app -> 'Crea una canzone ORIGINALE' ->")
            print("      motore 'Suno (i tuoi crediti gratuiti)'.")
            print("      (questa finestra deve restare aperta)")
            try:
                proc.wait()
            except KeyboardInterrupt:
                pass
            return 0
    print("      Il servizio non ha risposto entro 3 minuti. "
          "Guarda i messaggi sopra.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
