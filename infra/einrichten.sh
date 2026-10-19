#!/usr/bin/env bash
# Alles-in-einem-Einrichtung für die Google Cloud Shell. Fragt nacheinander alles ab.
#
#   git clone https://github.com/dannyclees/Make-Ersetzer.git && cd Make-Ersetzer && bash infra/einrichten.sh
#
# Vorher nötig (geht nur im Browser, siehe docs/EINRICHTUNG.md Schritt 1, 2 und 5a/5b):
#   - Projekt mit verknüpfter Abrechnung
#   - OAuth-Client (Desktop-App) als ~/client_secret.json in die Cloud Shell hochgeladen
set -euo pipefail
cd "$(dirname "$0")/.."

PROJECT_ID="${PROJECT_ID:-${DEVSHELL_PROJECT_ID:-$(gcloud config get project 2>/dev/null || true)}}"
read -r -p "Projekt-ID [${PROJECT_ID}]: " input && PROJECT_ID="${input:-$PROJECT_ID}"
read -r -p "E-Mail für Fehler-Alarme [consulting@cleesernster.com]: " ALERT_EMAIL
ALERT_EMAIL="${ALERT_EMAIL:-consulting@cleesernster.com}"
gcloud config set project "$PROJECT_ID" >/dev/null

if [ "$(gcloud billing projects describe "$PROJECT_ID" --format 'value(billingEnabled)' 2>/dev/null)" != "True" ]; then
  echo "Für $PROJECT_ID ist keine Abrechnung aktiv. Erst Schritt 2 in docs/EINRICHTUNG.md erledigen." >&2
  exit 1
fi

PROJECT_ID="$PROJECT_ID" ALERT_EMAIL="$ALERT_EMAIL" bash infra/setup.sh | tee /tmp/setup-ausgabe.txt

echo "==> monday-Zugang"
if gcloud secrets versions list monday-api-token --filter "state=ENABLED" --format "value(name)" | grep -q .; then
  echo "schon hinterlegt, übersprungen"
else
  read -r -s -p "monday-Token einfügen (Profilbild -> Entwickler -> Meine Zugriffstoken) und Enter: " T; echo
  printf %s "$T" | gcloud secrets versions add monday-api-token --data-file=- && unset T
fi

echo "==> Google-Drive-Zugang"
if gcloud secrets versions list google-oauth-user --filter "state=ENABLED" --format "value(name)" | grep -q .; then
  echo "schon hinterlegt, übersprungen"
else
  f="$(ls ~/client_secret*.json 2>/dev/null | head -1 || true)"
  if [ -z "$f" ]; then
    echo "Keine client_secret*.json im Home-Ordner. Schritt 5a/5b erledigen, Datei hochladen, Skript erneut starten." >&2
    exit 1
  fi
  pip install --user -q google-auth-oauthlib
  python3 scripts/google_oauth_token.py "$f" && rm -f "$f"
fi

echo
echo "Fertig. Jetzt nur noch die vier Werte oben (GCP_...) in GitHub eintragen, siehe docs/EINRICHTUNG.md Schritt 6."
