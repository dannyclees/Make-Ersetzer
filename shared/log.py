"""Strukturiertes JSON-Logging für Cloud Logging.

Cloud Run liest jede Zeile auf stdout als Log-Eintrag. Das Feld `severity`
steuert die Stufe; Einträge mit severity=ERROR und `alert=true` lösen über
die Log-basierte Alarm-Policy (siehe infra/setup.sh) eine E-Mail aus.
"""

import json
import sys
from datetime import datetime, timezone


def _emit(severity: str, message: str, **fields) -> None:
    entry = {
        "severity": severity,
        "message": message,
        "time": datetime.now(timezone.utc).isoformat(),
        **fields,
    }
    print(json.dumps(entry, default=str, ensure_ascii=False), file=sys.stdout, flush=True)


def info(message: str, **fields) -> None:
    _emit("INFO", message, **fields)


def warning(message: str, **fields) -> None:
    _emit("WARNING", message, **fields)


def error(message: str, **fields) -> None:
    _emit("ERROR", message, **fields)


def alert(message: str, **fields) -> None:
    """Fehler, bei dem ein Mensch benachrichtigt werden soll."""
    _emit("ERROR", message, alert=True, **fields)
