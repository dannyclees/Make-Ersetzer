# Make-Ersetzer: Regeln für neue Abläufe

Dieses Repo ersetzt Make/n8n/Zapier. Jeder Ablauf ist Python-Code, läuft auf
Google Cloud Run und wird per Push auf `main` automatisch deployt.

## Aufbau
- `<abteilung>/<ablauf>/` (z. B. `sales/onepage-zu-monday/`): ein Ordner pro Ablauf.
  Abteilungen: `marketing/`, `sales/`, `finance/`.
- Jeder Ablauf hat: `flow.yaml` (Steckbrief: Trigger, Secrets, Env, Ressourcen),
  `main.py` (HTTP-Einstieg), `flow.py` (Logik ohne HTTP, testbar), `Dockerfile`,
  `requirements.txt`, `tests/`. Vorbild: `sales/onepage-zu-monday/`.
- `shared/`: gemeinsamer Code. `log` (strukturierte Logs, `log.alert` = E-Mail-Alarm),
  `secrets` (liest Secrets aus Umgebungsvariablen), `retry.api_retry`,
  `deadletter.store`, `clients/monday.py`, `clients/google.py`.
- `infra/setup.sh`: einmalige GCP-Einrichtung. `scripts/`: Deploy, Tests, Replay, OAuth.

## Regeln
- Keine Zugangsdaten im Code oder Repo. Neue Secrets: im Secret Manager anlegen
  (`gcloud secrets create <name>`) und in `flow.yaml` unter `secrets:` eintragen.
- Nie echte Kundendaten in Tests oder Commits, nur erfundene Beispieldaten.
- Fehler nie verschlucken: vorübergehende Fehler über `api_retry` wiederholen;
  was danach noch scheitert, mit `deadletter.store` ablegen und `log.alert` melden.
- Abläufe müssen wiederholbar sein (idempotent): erneutes Einspielen derselben
  Eingabe darf nichts doppelt anlegen.
- Logik in `flow.py` mit injizierten Clients schreiben, damit Tests mit Fakes laufen.
- Vor jedem Commit: `bash scripts/test_all.sh`.
- Sprache in Code-Kommentaren, Logs und Doku: Deutsch.
