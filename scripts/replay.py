"""Spielt fehlgeschlagene Eingänge aus dem Dead-Letter-Bucket erneut ein.

  python scripts/replay.py onepage-zu-monday            # zeigt nur an
  python scripts/replay.py onepage-zu-monday --senden   # schickt erneut an den Webhook

Benötigt: PROJECT_ID, REGION, angemeldetes gcloud. Erfolgreich eingespielte
Dateien werden nach replayed/ verschoben. Doppelte Einträge verhindert der
Ablauf selbst (gleiche Anfrage -> gleiches Doc, gleiche E-Mail am selben Tag -> kein zweites Item).
"""

import json
import os
import subprocess
import sys

import requests
from google.cloud import storage


def gcloud(*args: str) -> str:
    return subprocess.run(["gcloud", *args], check=True, capture_output=True, text=True).stdout.strip()


def main(flow: str, send: bool) -> None:
    project, region = os.environ["PROJECT_ID"], os.environ["REGION"]
    bucket = storage.Client(project=project).bucket(f"{project}-deadletter")
    blobs = list(bucket.list_blobs(prefix=f"{flow}/"))
    if not blobs:
        print("Nichts einzuspielen.")
        return
    url = gcloud("run", "services", "describe", flow, "--region", region, "--format", "value(status.url)")
    token = gcloud("secrets", "versions", "access", "latest", "--secret", "onepage-webhook-token")

    for blob in blobs:
        entry = json.loads(blob.download_as_text())
        print(f"{blob.name}: {entry['reason'][:120]}")
        if not send:
            continue
        resp = requests.post(f"{url}/webhook", params={"token": token}, json=entry["payload"], timeout=120)
        print(f"  -> {resp.status_code} {resp.text[:200]}")
        if resp.ok and resp.json().get("status") in ("created", "duplicate"):
            bucket.copy_blob(blob, bucket, f"replayed/{blob.name}")
            blob.delete()


if __name__ == "__main__":
    main(sys.argv[1], "--senden" in sys.argv)
