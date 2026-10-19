# Einrichtung Schritt für Schritt

Dauer: ca. 45 Minuten, einmalig. Du brauchst nur einen Browser. Alle Befehle
laufen in der **Google Cloud Shell**, einem Terminal im Browser, das Google
gratis stellt. Auf deinem Rechner musst du nichts installieren.

Mach alles mit dem Google-Konto, dem der Drive-Ordner **„Anfragen Doks“**
gehört (`danny.clees.ypr@gmail.com`).

---

## Schritt 1: Google-Cloud-Projekt anlegen (5 Min.)

1. Öffne <https://console.cloud.google.com> und melde dich an.
   Beim ersten Mal: Land **Luxemburg** wählen, Nutzungsbedingungen akzeptieren.
2. Oben links neben „Google Cloud“ auf die **Projektauswahl** klicken → **Neues Projekt**.
3. Projektname: `hausman-automation` (oder frei wählbar). Unter dem Namen steht die
   **Projekt-ID**, z. B. `hausman-automation-471512`. **Diese ID notieren**, du brauchst sie gleich.
4. **Erstellen** klicken und warten, bis oben rechts die Glocke „Projekt erstellt“ meldet.
5. Oben in der Projektauswahl sicherstellen, dass **das neue Projekt ausgewählt** ist.

## Schritt 2: Abrechnung aktivieren (5 Min.)

Cloud Run kostet bei unseren Mengen praktisch nichts, die Gratis-Kontingente
reichen bei weitem. Google verlangt trotzdem ein Rechnungskonto.

1. Links im Menü (☰) → **Abrechnung**.
2. „Dieses Projekt hat kein Rechnungskonto“ → **Rechnungskonto verknüpfen** →
   **Rechnungskonto erstellen**.
3. Kontotyp **Unternehmen**, Firmendaten und Kreditkarte eingeben → **Senden und Abrechnung aktivieren**.
4. **Budget-Warnung** (empfohlen): Abrechnung → **Budgets & Benachrichtigungen** →
   **Budget erstellen** → Name „Automatisierung“, Betrag **10 €** → bei 50 %, 90 % und 100 %
   E-Mail-Warnung → **Fertigstellen**. Ein Budget stoppt nichts, du bekommst aber sofort Bescheid.

## Schritt 3: Cloud Shell öffnen und das Setup-Skript ausführen (10 Min.)

1. Oben rechts in der Console auf das Symbol **`>_`** („Cloud Shell aktivieren“) klicken.
   Unten öffnet sich ein Terminal. Beim ersten Mal **Weiter / Autorisieren** klicken.
2. Folgende Zeilen **einzeln** einfügen (Einfügen im Terminal: Strg+V bzw. Cmd+V) und mit
   Enter bestätigen. `DEINE-PROJEKT-ID` und die E-Mail ersetzen:

   ```bash
   git clone https://github.com/dannyclees/Make-Ersetzer.git
   cd Make-Ersetzer
   gcloud config set project DEINE-PROJEKT-ID
   PROJECT_ID=DEINE-PROJEKT-ID ALERT_EMAIL=consulting@cleesernster.com bash infra/setup.sh
   ```

   Fragt GitHub beim Klonen nach einem Login, ist das Repo privat. Dann so klonen:
   GitHub → Profilbild → Settings → Developer settings → **Personal access tokens →
   Fine-grained** → Token nur für `Make-Ersetzer` mit „Contents: Read“ erstellen, und dann
   `git clone https://<TOKEN>@github.com/dannyclees/Make-Ersetzer.git`.

3. Das Skript läuft 3–5 Minuten. Fragt es „API … aktivieren? (y/N)“, mit **y** antworten.
4. Am Ende stehen **vier Werte** (`GCP_PROJECT_ID`, `GCP_REGION`, `GCP_WIF_PROVIDER`,
   `GCP_DEPLOY_SA`). **Fenster offen lassen** oder die Werte kopieren, du brauchst sie in Schritt 6.

Das Skript hat jetzt angelegt:
- den Server-Bereich (Cloud Run) in Belgien (`europe-west1`, nahe Luxemburg, günstigster Tarif)
- den Secret Manager mit drei leeren „Tresorfächern“ für die Zugänge
- den Fehler-Alarm per E-Mail
- den Ablageort für fehlgeschlagene Anfragen (90 Tage)
- den schlüssellosen Zugang für GitHub

## Schritt 4: monday-Zugang hinterlegen (3 Min.)

1. In monday: unten links auf dein **Profilbild** → **Entwickler** → oben **Meine Zugriffstoken**
   → **Anzeigen** → **Kopieren**.
   (Alternativ: Profilbild → Administration → Verbindungen → **API**.)
2. In der Cloud Shell:

   ```bash
   read -s -p "monday-Token einfügen und Enter: " T && printf %s "$T" | gcloud secrets versions add monday-api-token --data-file=- && unset T
   ```

   Beim Einfügen siehst du nichts, das ist Absicht. Einfach Strg+V und Enter.

## Schritt 5: Google-Drive-Zugang hinterlegen (10 Min.)

Damit die Docs wie bisher **in deinem Drive** im Ordner „Anfragen Doks“ landen,
braucht der Ablauf deine Erlaubnis, einmalig.

**5a: Zustimmungsbildschirm einrichten**
1. Console-Menü (☰) → **APIs & Dienste** → **OAuth-Zustimmungsbildschirm**
   (heißt teils **Google Auth Platform**) → **Jetzt starten**.
2. App-Name `Hausman Automatisierung`, Support-E-Mail: deine → **Weiter**.
3. Zielgruppe: **Extern** → **Weiter** → Kontakt-E-Mail: deine → **Weiter** → zustimmen → **Erstellen**.
4. Links **Zielgruppe** (Audience) → unter „Veröffentlichungsstatus“ **App veröffentlichen** →
   **Bestätigen**. Status muss **„In Produktion“** sein.
   **Das ist wichtig:** Im Status „Testen“ läuft der Zugang nach 7 Tagen ab.

**5b: Zugangsdaten (Client) erstellen**
1. Links **Clients** → **Client erstellen** (bzw. APIs & Dienste → Anmeldedaten →
   Anmeldedaten erstellen → OAuth-Client-ID).
2. Anwendungstyp **Desktop-App**, Name `cloud-shell` → **Erstellen**.
3. Im Fenster **JSON herunterladen** klicken. Die Datei landet in deinem Download-Ordner.

**5c: In der Cloud Shell einlösen**
1. In der Cloud Shell oben rechts auf **⋮ (Mehr)** → **Hochladen** → die eben geladene
   JSON-Datei auswählen. Sie landet in deinem Home-Ordner.
2. Dann:

   ```bash
   mv ~/client_secret_*.json ~/client_secret.json
   pip install --user -q google-auth-oauthlib
   python3 scripts/google_oauth_token.py ~/client_secret.json
   ```

3. Das Skript zeigt einen langen Link. **Link anklicken** → mit dem Konto anmelden, dem
   „Anfragen Doks“ gehört.
4. Hinweis „Google hat diese App nicht überprüft“ → **Erweitert** → **Zu Hausman Automatisierung
   wechseln (unsicher)**. Das ist deine eigene App, das ist unbedenklich. Dann **Weiter / Zulassen**.
5. Der Browser zeigt danach **„Diese Seite ist nicht erreichbar“** (localhost). **Das ist richtig so.**
   Die **komplette Adresse aus der Adresszeile** kopieren (beginnt mit `http://localhost:1/?state=…`),
   ins Cloud-Shell-Fenster einfügen und Enter.
6. Meldung „Gespeichert im Secret Manager“ → danach `rm ~/client_secret.json`.

## Schritt 6: GitHub mit Google Cloud verbinden (5 Min.)

1. Öffne <https://github.com/dannyclees/Make-Ersetzer> → **Settings** → links
   **Secrets and variables** → **Actions** → Reiter **Variables** → **New repository variable**.
2. Viermal anlegen, Name und Wert exakt aus der Ausgabe von Schritt 3:

   | Name | Beispielwert |
   |---|---|
   | `GCP_PROJECT_ID` | `hausman-automation-471512` |
   | `GCP_REGION` | `europe-west1` |
   | `GCP_WIF_PROVIDER` | `projects/123456789/locations/global/workloadIdentityPools/github/providers/github-actions` |
   | `GCP_DEPLOY_SA` | `github-deployer@hausman-automation-471512.iam.gserviceaccount.com` |

   Das sind keine Passwörter, nur Adressen. Die eigentlichen Zugänge bleiben im Secret Manager.
3. Der Code muss auf dem Branch **`main`** liegen, sonst wird nicht deployt.
4. Reiter **Actions** → links **Deploy** → **Run workflow** → **Run workflow**.
   Nach ca. 3 Minuten hat es einen grünen Haken. Rot? Den Fehler an Claude schicken.

## Schritt 7: Testen, bevor OnePage angeschlossen wird (5 Min.)

In der Cloud Shell eine erfundene Test-Anfrage schicken:

```bash
URL=$(gcloud run services describe onepage-zu-monday --region europe-west1 --format 'value(status.url)')
TOKEN=$(gcloud secrets versions access latest --secret onepage-webhook-token)
curl -s -X POST "$URL/webhook?token=$TOKEN" -H 'Content-Type: application/json' -d '{
  "process": "Website-Anfrage",
  "fields": [
    {"label": "Name", "value": "TEST Bitte löschen"},
    {"label": "E-Mail", "value": "test@example.com"},
    {"label": "Telefon", "value": "691000000"},
    {"label": "Für welchen Bereich interessierst Du Dich?", "value": "Klima"},
    {"label": "Wann dürfen wir Dich am besten erreichen?", "value": "Flexibel"}
  ]}'
```

Erwartet: `{"status":"created","category":"klima",...}`. Im Klima-Board steht dann
„TEST Bitte löschen“ mit Doc-Link, und in „Anfragen Doks“ liegt das Doc. Danach beides löschen.

## Schritt 8: OnePage anschließen (5 Min.)

1. Die Webhook-Adresse anzeigen lassen:

   ```bash
   echo "$URL/webhook?token=$TOKEN"
   ```

2. In OnePage: **CRM** → **Integrationen** (bzw. Einstellungen → Integrationen) →
   **Integration hinzufügen** → **Webhook** → die Adresse einfügen → als Auslöser
   „neuer Lead / neue Anfrage“ im Prozess **Website-Anfrage** wählen → speichern.
3. Eine echte Test-Anfrage über hausman.lu abschicken.
4. Prüfen: Console → **Cloud Run** → `onepage-zu-monday` → **Logs**. Dort steht das
   komplette Payload („Payload empfangen“). **Dieses Log an Claude schicken.** Damit wird die
   Feldzuordnung exakt festgezurrt, z. B. Name, Anrede und Eingangsdatum.

## Was im Alltag passiert

- **Alles gut:** Neue Anfrage → nach wenigen Sekunden Doc + Eintrag im richtigen Board.
- **Fehler:** Du bekommst eine E-Mail „Automatisierung fehlgeschlagen“. Die Anfrage geht nicht
  verloren, sie liegt gespeichert in Cloud Storage. Nach dem Beheben in der Cloud Shell:

  ```bash
  cd Make-Ersetzer && pip install --user -q google-cloud-storage requests
  PROJECT_ID=$(gcloud config get project) REGION=europe-west1 \
    python3 scripts/replay.py onepage-zu-monday --senden
  ```

- **Anfrage passt in kein Board:** ebenfalls E-Mail. Dann die Regeln in
  `sales/onepage-zu-monday/boards.yaml` ergänzen, oder Claude sagen, wohin sie gehört.
