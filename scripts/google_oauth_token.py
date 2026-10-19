"""Erzeugt einmalig den Google-Zugang, mit dem die Abläufe Docs in deiner Ablage anlegen.

Auf dem eigenen Rechner ausführen (öffnet den Browser zum Anmelden):

  pip install google-auth-oauthlib
  python scripts/google_oauth_token.py client_secret.json \
    | gcloud secrets versions add google-oauth-user --data-file=-

client_secret.json = OAuth-Client vom Typ "Desktop-App" (siehe README, Schritt 3).
Die Datei danach löschen; sie gehört nie ins Repo.
"""

import json
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/drive"]

if __name__ == "__main__":
    flow = InstalledAppFlow.from_client_secrets_file(sys.argv[1], SCOPES)
    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
    if not creds.refresh_token:
        sys.exit("Kein Refresh-Token erhalten. App-Zugriff unter myaccount.google.com/permissions entfernen und neu starten.")
    print(json.dumps({"client_id": creds.client_id, "client_secret": creds.client_secret,
                      "refresh_token": creds.refresh_token}), end="")
