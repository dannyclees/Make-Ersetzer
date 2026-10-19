"""Zugriff auf Zugangsdaten.

Cloud Run bindet Secrets aus dem Google Secret Manager als Umgebungsvariablen
ein (`--set-secrets`, siehe flow.yaml des jeweiligen Ablaufs). Im Code steht
daher nie ein Schlüssel, nur der Name der Variable.
"""

import json
import os


class MissingSecret(RuntimeError):
    pass


def get(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise MissingSecret(f"Secret/Umgebungsvariable {name} ist nicht gesetzt")
    return value.strip()


def get_json(name: str) -> dict:
    return json.loads(get(name))
