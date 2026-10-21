# -*- coding: utf-8 -*-
"""
accesso.py
==========
Password di accesso a CANTICO.

Qui c'e' SOLO l'hash SHA-256 della password: la password in chiaro non e'
scritta da nessuna parte. Se sbagli la password puoi cambiarla:
    1. genera un nuovo hash:
       python -c "import hashlib;print(hashlib.sha256('NUA-PASSWORD'.encode()).hexdigest())"
    2. incolla l'hash qui sotto
    3. carica il file su GitHub: l'app si aggiorna da sola.

La password si puo' cambiare anche dal pannello di Streamlit Cloud
(Settings -> Secrets -> APP_PASSWORD_SHA256), che ha la precedenza.
"""

PASSWORD_SHA256 = "f96d0d01a1e45808de6f8b76991d303f4f35772cd1751d6ef049b71226fda383"
