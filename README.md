# Make-Ersetzer

Unsere Automatisierungen als Code statt in Make: Claude Code schreibt die
Abläufe, GitHub ist die Ablage, Google Cloud Run führt sie aus, der Google
Secret Manager hält die Zugänge. Bei unseren Mengen bleibt das fast immer im
kostenlosen Kontingent von Cloud Run.

| Abteilung | Ablauf | Was er tut |
|---|---|---|
| sales | [`onepage-zu-monday`](sales/onepage-zu-monday/) | Neue Website-Anfrage aus dem OnePage-CRM (hausman.lu) → Google-Doc mit allen Antworten → Eintrag im passenden monday-Board (Badezimmer, Klima, Innenausbau, Wärmepumpe, Recruiting) |

## So funktioniert ein Ablauf

```
OnePage-CRM ──Webhook──▶ Cloud Run (sales/onepage-zu-monday)
                            ├─ Google-Doc in "Anfragen Doks" anlegen
                            ├─ Kategorie aus den Antworten bestimmen (boards.yaml)
                            ├─ Eintrag im monday-Board (Badezimmer / Klima / Innenausbau / Wärmepumpe / Recruiting)
                            └─ bei Fehler: Wiederholversuche → Ablage im Dead-Letter-Bucket → E-Mail-Alarm
```

Neuer Ablauf: Claude Code in normalen Worten sagen, was passieren soll. Die
Regeln dafür stehen in [`CLAUDE.md`](CLAUDE.md). Push auf `main` deployt automatisch.

## Einrichtung (einmalig)

Schritt-für-Schritt-Anleitung, nur mit dem Browser: **[docs/EINRICHTUNG.md](docs/EINRICHTUNG.md)**

## Betrieb

- **Fehler:** Du bekommst eine E-Mail. Der Eingang liegt im Bucket `<projekt-id>-deadletter`.
  Nach dem Beheben erneut einspielen:
  `PROJECT_ID=… REGION=europe-west1 python scripts/replay.py onepage-zu-monday --senden`
- **Tests lokal:** `pip install pytest -r sales/onepage-zu-monday/requirements.txt && bash scripts/test_all.sh`
- **Manuell deployen:** `PROJECT_ID=… REGION=europe-west1 python scripts/deploy_flow.py sales/onepage-zu-monday`
