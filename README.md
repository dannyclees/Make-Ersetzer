# Make-Ersetzer

Unsere Automatisierungen als Code statt in Make: Claude Code schreibt die
Abläufe, GitHub ist die Ablage, Google Cloud Run führt sie aus, der Google
Secret Manager hält die Zugänge. Bei unseren Mengen bleibt das fast immer im
kostenlosen Kontingent von Cloud Run.

| Abteilung | Ablauf | Was er tut |
|---|---|---|
| sales | [`onepage-zu-monday`](sales/onepage-zu-monday/) | Neue Anfrage aus dem OnePage-CRM (hausman.lu) → Google-Doc mit allen Antworten → Eintrag im passenden monday-Board |

## So funktioniert ein Ablauf

```
OnePage-CRM ──Webhook──▶ Cloud Run (sales/onepage-zu-monday)
                            ├─ Google-Doc in "Anfragen Doks" anlegen
                            ├─ Eintrag im monday-Board (Badezimmer / Klima / Innenausbau / Wärmepumpe)
                            └─ bei Fehler: Wiederholversuche → Ablage im Dead-Letter-Bucket → E-Mail-Alarm
```

Neuer Ablauf: Claude Code in normalen Worten sagen, was passieren soll. Die
Regeln dafür stehen in [`CLAUDE.md`](CLAUDE.md). Push auf `main` deployt automatisch.

## Einrichtung (einmalig)

### 1. Google-Cloud-Projekt mit Abrechnung
1. <https://console.cloud.google.com> → oben „Projekt auswählen“ → **Neues Projekt**,
   z. B. `cleesernster-automation`. Die **Projekt-ID** notieren.
2. **Abrechnung** → Rechnungskonto anlegen (Kreditkarte) und mit dem Projekt verknüpfen.
3. Empfehlung: **Abrechnung → Budgets & Benachrichtigungen** → Budget 10 € / Monat mit E-Mail-Warnung.

### 2. Setup-Skript in der Cloud Shell
Oben rechts in der Console auf **`>_` (Cloud Shell aktivieren)**, dann:

```bash
git clone https://github.com/dannyclees/Make-Ersetzer.git && cd Make-Ersetzer
PROJECT_ID=<projekt-id> ALERT_EMAIL=<deine@mail> bash infra/setup.sh
```

Das Skript aktiviert die Dienste und legt Folgendes an: Service-Accounts, den
schlüssellosen GitHub-Zugang, den Bucket für Fehlerfälle, die Secrets und den
E-Mail-Alarm. Am Ende gibt es vier Werte für Schritt 4 aus. Die Bestätigungsmail
von Google Cloud Monitoring an `ALERT_EMAIL` musst du nicht bestätigen. Kommt sie
im Spam an, als „kein Spam“ markieren.

### 3. Zugänge hinterlegen
**monday:** In monday auf Profilbild → **Entwickler** → **Meine Zugriffstoken** → kopieren:
```bash
read -s T && printf %s "$T" | gcloud secrets versions add monday-api-token --data-file=-
```

**Google Drive** (damit Docs in *deiner* Ablage landen, wie bisher):
1. Console → **APIs & Dienste → OAuth-Zustimmungsbildschirm**: Typ *Extern*, App-Name z. B.
   „Automatisierungen“, deine E-Mail eintragen. Danach **Veröffentlichungsstatus → „In Produktion“**.
   Im Testmodus läuft der Zugang nach 7 Tagen ab.
2. **APIs & Dienste → Anmeldedaten → Anmeldedaten erstellen → OAuth-Client-ID**, Typ
   **Desktop-App** → JSON herunterladen als `client_secret.json`.
3. Auf deinem Rechner (mit installiertem [gcloud](https://cloud.google.com/sdk/docs/install)):
   ```bash
   pip install google-auth-oauthlib
   python scripts/google_oauth_token.py client_secret.json \
     | gcloud secrets versions add google-oauth-user --data-file=- --project <projekt-id>
   ```
   Mit dem Google-Konto anmelden, dem der Ordner „Anfragen Doks“ gehört. Den Hinweis
   „Google hat diese App nicht überprüft“ mit *Erweitert → Weiter* bestätigen, denn es ist deine
   eigene App. Danach `client_secret.json` löschen.

### 4. GitHub verbinden
Repo → **Settings → Secrets and variables → Actions → Variables** → die vier Werte
aus Schritt 2 eintragen (`GCP_PROJECT_ID`, `GCP_REGION`, `GCP_WIF_PROVIDER`, `GCP_DEPLOY_SA`).
Danach **Actions → Deploy → Run workflow**. Ab jetzt deployt jeder Push auf `main` automatisch.

### 5. OnePage anschließen
```bash
URL=$(gcloud run services describe onepage-zu-monday --region europe-west1 --format 'value(status.url)')
TOKEN=$(gcloud secrets versions access latest --secret onepage-webhook-token)
echo "$URL/webhook?token=$TOKEN"
```
Diese URL in OnePage unter **CRM → Integrationen → Webhook hinzufügen** eintragen.

### 6. Parallelbetrieb, dann Make abschalten
- Eine Test-Anfrage über hausman.lu schicken. Im Log
  (**Cloud Run → onepage-zu-monday → Logs**) erscheint das komplette Payload, weil
  `LOG_PAYLOAD=1` gesetzt ist. Damit wird die Feldzuordnung in `lead.py` final festgezurrt.
- Ein bis zwei Wochen parallel zu Make laufen lassen. Dafür in `boards.yaml` vorübergehend ein
  Test-Board eintragen, sonst entstehen doppelte Einträge.
- Passt alles: Make-Szenario aus, `LOG_PAYLOAD` auf `"0"`, echte Boards eintragen.

## Betrieb

- **Fehler:** Du bekommst eine E-Mail. Der Eingang liegt im Bucket `<projekt-id>-deadletter`.
  Nach dem Beheben erneut einspielen:
  `PROJECT_ID=… REGION=europe-west1 python scripts/replay.py onepage-zu-monday --senden`
- **Tests lokal:** `pip install pytest -r sales/onepage-zu-monday/requirements.txt && bash scripts/test_all.sh`
- **Manuell deployen:** `PROJECT_ID=… REGION=europe-west1 python scripts/deploy_flow.py sales/onepage-zu-monday`
