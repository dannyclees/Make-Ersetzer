"""Erzeugt einmalig den Google-Zugang, mit dem die Abläufe Docs in deiner Ablage anlegen,
und speichert ihn direkt im Secret Manager (Secret `google-oauth-user`).

Läuft in der Google Cloud Shell, ohne Installation auf dem eigenen Rechner:

  pip install --user google-auth-oauthlib
  python3 scripts/google_oauth_token.py ~/client_secret.json

Ablauf: Link öffnen, mit dem Google-Konto anmelden, dem "Anfragen Doks" gehört,
zustimmen. Danach zeigt der Browser "Diese Seite ist nicht erreichbar". Das ist
richtig so. Die komplette Adresse aus der Adresszeile kopieren und hier einfügen.
"""

import json
import os
import subprocess
import sys

from google_auth_oauthlib.flow import Flow

SCOPES = ["https://www.googleapis.com/auth/drive"]
REDIRECT = "http://localhost:1"  # wird nie wirklich aufgerufen, wir lesen nur den Code aus der Adresse

if __name__ == "__main__":
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # nur für die localhost-Weiterleitung
    flow = Flow.from_client_secrets_file(sys.argv[1], SCOPES, redirect_uri=REDIRECT)
    url, _ = flow.authorization_url(access_type="offline", prompt="consent")
    print("\n1) Diesen Link im Browser öffnen:\n\n" + url + "\n")
    response = input("2) Adresse aus der Adresszeile (beginnt mit http://localhost:1/?...) hier einfügen:\n> ").strip()
    flow.fetch_token(authorization_response=response)
    creds = flow.credentials
    if not creds.refresh_token:
        sys.exit("Kein Refresh-Token erhalten. Unter myaccount.google.com/permissions den Zugriff der App "
                 "entfernen und das Skript neu starten.")
    secret = json.dumps({"client_id": creds.client_id, "client_secret": creds.client_secret,
                         "refresh_token": creds.refresh_token})
    subprocess.run(["gcloud", "secrets", "versions", "add", "google-oauth-user", "--data-file=-"],
                   input=secret, text=True, check=True)
    print("\nGespeichert im Secret Manager (google-oauth-user). client_secret.json kann jetzt gelöscht werden:")
    print(f"  rm {sys.argv[1]}")
