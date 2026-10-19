"""Ablage für Eingänge, die nicht verarbeitet werden konnten.

Jeder fehlgeschlagene Payload landet als JSON im Bucket
`gs://$DEADLETTER_BUCKET/<flow>/<zeit>-<id>.json` und kann später mit
scripts/replay.py erneut eingespielt werden. So geht keine Anfrage verloren.
"""

import json
import os
from datetime import datetime, timezone

from shared import log


def store(flow: str, key: str, payload: dict, reason: str) -> str | None:
    bucket_name = os.environ.get("DEADLETTER_BUCKET")
    if not bucket_name:
        log.warning("DEADLETTER_BUCKET nicht gesetzt, Payload wird nur geloggt", flow=flow, key=key)
        return None
    from google.cloud import storage  # erst hier importieren, damit Tests ohne GCP laufen

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = f"{flow}/{stamp}-{key}.json"
    blob = storage.Client().bucket(bucket_name).blob(path)
    blob.upload_from_string(
        json.dumps({"reason": reason, "payload": payload}, ensure_ascii=False, indent=2),
        content_type="application/json",
    )
    return f"gs://{bucket_name}/{path}"
