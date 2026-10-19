"""HTTP-Einstieg (Cloud Run): OnePage schickt jede neue CRM-Anfrage per Webhook hierher.

POST /webhook?token=<ONEPAGE_WEBHOOK_TOKEN>
"""

import hmac
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # Repo-Wurzel, damit `shared` importierbar ist

from flask import Flask, jsonify, request  # noqa: E402

import flow  # noqa: E402
from lead import payload_key  # noqa: E402
from shared import deadletter, log, secrets  # noqa: E402
from shared.clients.google import Drive, user_credentials  # noqa: E402
from shared.clients.monday import MondayClient  # noqa: E402

app = Flask(__name__)
_clients = {}


def _get_clients():
    if not _clients:
        _clients["monday"] = MondayClient(secrets.get("MONDAY_API_TOKEN"))
        _clients["drive"] = Drive(user_credentials(secrets.get_json("GOOGLE_OAUTH_USER")))
    return _clients["monday"], _clients["drive"]


def _authorized(payload: dict) -> bool:
    expected = secrets.get("ONEPAGE_WEBHOOK_TOKEN")
    given = (
        request.args.get("token")
        or request.headers.get("X-Webhook-Token")
        or str(payload.get("secretkey") or payload.get("secret") or "")
    )
    return bool(given) and hmac.compare_digest(given, expected)


@app.get("/healthz")
def healthz():
    return "ok"


@app.post("/webhook")
def webhook():
    payload = request.get_json(silent=True)
    if payload is None:
        payload = request.form.to_dict(flat=True)
    if not isinstance(payload, dict):
        payload = {"data": payload}

    if not _authorized(payload):
        log.warning("Webhook ohne gültiges Token abgelehnt", flow=flow.FLOW)
        return jsonify(error="unauthorized"), 401

    payload.pop("secretkey", None)
    payload.pop("secret", None)
    key = payload_key(payload)
    if os.environ.get("LOG_PAYLOAD") == "1":  # nur in der Einrichtungsphase: zeigt das echte OnePage-Format
        log.info("Payload empfangen", flow=flow.FLOW, key=key, payload=payload)
    else:
        log.info("Payload empfangen", flow=flow.FLOW, key=key, fields=sorted(payload.keys()))

    try:
        monday, drive = _get_clients()
        result = flow.handle(payload, monday, drive)
        return jsonify(status=result.status, category=result.category, item_id=result.item_id)
    except flow.Unroutable as exc:
        # Nochmal schicken hilft nicht -> 200, aber ablegen und Alarm.
        where = deadletter.store(flow.FLOW, key, payload, str(exc))
        log.alert("Anfrage konnte keinem Board zugeordnet werden", flow=flow.FLOW, key=key, error=str(exc),
                  deadletter=where)
        return jsonify(status="unroutable", deadletter=where)
    except Exception as exc:
        where = None
        try:
            where = deadletter.store(flow.FLOW, key, payload, repr(exc))
        finally:
            log.alert("Anfrage konnte nicht verarbeitet werden", flow=flow.FLOW, key=key, error=repr(exc),
                      deadletter=where)
        return jsonify(status="error", deadletter=where), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
