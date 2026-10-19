#!/usr/bin/env bash
# Einmalige Einrichtung des Google-Cloud-Projekts.
# In der Google Cloud Shell ausführen (console.cloud.google.com -> Symbol ">_" oben rechts):
#
#   git clone https://github.com/dannyclees/Make-Ersetzer.git && cd Make-Ersetzer
#   PROJECT_ID=<projekt-id> ALERT_EMAIL=<deine@mail> bash infra/setup.sh
#
# Das Skript ist wiederholbar: bereits Vorhandenes wird übersprungen.
set -euo pipefail

: "${PROJECT_ID:?PROJECT_ID setzen}"
: "${ALERT_EMAIL:?ALERT_EMAIL setzen (bekommt Fehler-Alarme)}"
REGION="${REGION:-europe-west1}"
GITHUB_REPO="${GITHUB_REPO:-dannyclees/Make-Ersetzer}"

RUNTIME_SA="flows-runtime@${PROJECT_ID}.iam.gserviceaccount.com"
DEPLOY_SA="github-deployer@${PROJECT_ID}.iam.gserviceaccount.com"
BUCKET="${PROJECT_ID}-deadletter"

gcloud config set project "$PROJECT_ID" >/dev/null
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"

echo "==> APIs aktivieren"
gcloud services enable run.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com \
  iam.googleapis.com iamcredentials.googleapis.com sts.googleapis.com storage.googleapis.com \
  logging.googleapis.com monitoring.googleapis.com cloudscheduler.googleapis.com drive.googleapis.com

echo "==> Artifact Registry (Container-Images)"
gcloud artifacts repositories describe flows --location "$REGION" >/dev/null 2>&1 ||
  gcloud artifacts repositories create flows --repository-format docker --location "$REGION" \
    --description "Images der Automatisierungen"

echo "==> Service-Accounts"
gcloud iam service-accounts describe "$RUNTIME_SA" >/dev/null 2>&1 ||
  gcloud iam service-accounts create flows-runtime --display-name "Laufzeit der Automatisierungen"
gcloud iam service-accounts describe "$DEPLOY_SA" >/dev/null 2>&1 ||
  gcloud iam service-accounts create github-deployer --display-name "GitHub Actions Deploy"

gcloud projects add-iam-policy-binding "$PROJECT_ID" --member "serviceAccount:$RUNTIME_SA" \
  --role roles/secretmanager.secretAccessor --condition None >/dev/null
for role in roles/run.admin roles/artifactregistry.writer; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --member "serviceAccount:$DEPLOY_SA" \
    --role "$role" --condition None >/dev/null
done
gcloud iam service-accounts add-iam-policy-binding "$RUNTIME_SA" \
  --member "serviceAccount:$DEPLOY_SA" --role roles/iam.serviceAccountUser >/dev/null

echo "==> GitHub darf ohne Schlüsseldatei deployen (Workload Identity Federation)"
gcloud iam workload-identity-pools describe github --location global >/dev/null 2>&1 ||
  gcloud iam workload-identity-pools create github --location global --display-name "GitHub"
gcloud iam workload-identity-pools providers describe github-actions --location global \
  --workload-identity-pool github >/dev/null 2>&1 ||
  gcloud iam workload-identity-pools providers create-oidc github-actions --location global \
    --workload-identity-pool github --issuer-uri "https://token.actions.githubusercontent.com" \
    --attribute-mapping "google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
    --attribute-condition "assertion.repository == '${GITHUB_REPO}'"
gcloud iam service-accounts add-iam-policy-binding "$DEPLOY_SA" --role roles/iam.workloadIdentityUser \
  --member "principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github/attribute.repository/${GITHUB_REPO}" \
  >/dev/null

echo "==> Bucket für fehlgeschlagene Anfragen (90 Tage Aufbewahrung)"
gcloud storage buckets describe "gs://$BUCKET" >/dev/null 2>&1 ||
  gcloud storage buckets create "gs://$BUCKET" --location "$REGION" --uniform-bucket-level-access
echo '{"rule":[{"action":{"type":"Delete"},"condition":{"age":90}}]}' > /tmp/lifecycle.json
gcloud storage buckets update "gs://$BUCKET" --lifecycle-file /tmp/lifecycle.json >/dev/null
gcloud storage buckets add-iam-policy-binding "gs://$BUCKET" --member "serviceAccount:$RUNTIME_SA" \
  --role roles/storage.objectAdmin >/dev/null

echo "==> Secrets anlegen (Werte kommen in Schritt 3 der README)"
for s in monday-api-token google-oauth-user onepage-webhook-token; do
  gcloud secrets describe "$s" >/dev/null 2>&1 || gcloud secrets create "$s" --replication-policy automatic
done
if ! gcloud secrets versions list onepage-webhook-token --filter "state=ENABLED" --format "value(name)" | grep -q .; then
  openssl rand -hex 24 | tr -d '\n' | gcloud secrets versions add onepage-webhook-token --data-file=-
fi

echo "==> Alarm per E-Mail bei Fehlern"
CHANNEL="$(gcloud beta monitoring channels list --filter "labels.email_address=${ALERT_EMAIL}" --format 'value(name)' | head -1)"
if [ -z "$CHANNEL" ]; then
  CHANNEL="$(gcloud beta monitoring channels create --display-name "Automatisierungen: ${ALERT_EMAIL}" \
    --type email --channel-labels "email_address=${ALERT_EMAIL}" --format 'value(name)')"
fi
if ! gcloud alpha monitoring policies list --filter 'displayName="Automatisierung fehlgeschlagen"' \
     --format 'value(name)' | grep -q .; then
  cat > /tmp/policy.json <<EOF
{
  "displayName": "Automatisierung fehlgeschlagen",
  "combiner": "OR",
  "conditions": [{
    "displayName": "Log mit alert=true",
    "conditionMatchedLog": {
      "filter": "resource.type=\"cloud_run_revision\" AND severity>=ERROR AND jsonPayload.alert=true",
      "labelExtractors": {"flow": "EXTRACT(jsonPayload.flow)", "fehler": "EXTRACT(jsonPayload.message)"}
    }
  }],
  "alertStrategy": {"notificationRateLimit": {"period": "300s"}, "autoClose": "1800s"},
  "notificationChannels": ["${CHANNEL}"],
  "documentation": {"content": "Eine Automatisierung ist fehlgeschlagen. Details im Log (Feld deadletter zeigt den gespeicherten Eingang). Erneut einspielen: scripts/replay.py", "mimeType": "text/markdown"}
}
EOF
  gcloud alpha monitoring policies create --policy-from-file /tmp/policy.json >/dev/null
fi

cat <<EOF

Fertig. Diese Werte in GitHub eintragen
(Repo -> Settings -> Secrets and variables -> Actions -> Tab "Variables"):

  GCP_PROJECT_ID    = ${PROJECT_ID}
  GCP_REGION        = ${REGION}
  GCP_WIF_PROVIDER  = projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github/providers/github-actions
  GCP_DEPLOY_SA     = ${DEPLOY_SA}

EOF
