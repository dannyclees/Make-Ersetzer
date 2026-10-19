"""Ablauf: neue Anfrage aus OnePage -> Google-Doc + Eintrag im passenden monday-Board."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from doc import render_html
from lead import Lead, parse, route
from shared import log

FLOW = "onepage-zu-monday"
CONFIG = yaml.safe_load((Path(__file__).parent / "boards.yaml").read_text(encoding="utf-8"))


class Unroutable(Exception):
    """Anfrage lässt sich keinem Board zuordnen."""


@dataclass
class Result:
    status: str  # "created" | "duplicate"
    category: str
    item_id: str
    doc_url: str


def handle(payload: dict, monday, drive, config: dict = CONFIG, today: str | None = None) -> Result:
    lead = parse(payload)
    category = route(lead, config["categories"])
    if category is None:
        raise Unroutable(f"Keine Kategorie passt zu: {lead.routing_text[:200]!r}")
    cat = config["categories"][category]
    cols = cat["columns"]
    today = today or datetime.now(ZoneInfo(config["timezone"])).date().isoformat()
    log.info("Anfrage erkannt", flow=FLOW, key=lead.key, category=category, answers=len(lead.answers))

    doc = _ensure_doc(lead, drive, config["drive_folder_id"])

    existing = _find_existing_item(lead, monday, cat, today)
    if existing:
        log.info("Eintrag existiert schon, nichts doppelt angelegt", flow=FLOW, key=lead.key, item_id=existing)
        return Result("duplicate", category, existing, doc["webViewLink"])

    values = {cols["status"]: {"label": cat["status_label"]}, cols["date"]: {"date": today}}
    if cols.get("auftrag"):
        values[cols["auftrag"]] = cat["label"]
    if lead.email and cols.get("email"):
        values[cols["email"]] = {"email": lead.email, "text": lead.email}
    if lead.phone and cols.get("phone"):
        values[cols["phone"]] = _phone_value(lead.phone)
    item_id = monday.create_item(cat["board_id"], cat["group_id"], lead.name, values)

    _attach_doc(monday, cat, item_id, lead, doc["webViewLink"])
    log.info("Anfrage in monday angelegt", flow=FLOW, key=lead.key, board=cat["board_id"], item_id=item_id)
    return Result("created", category, item_id, doc["webViewLink"])


def _ensure_doc(lead: Lead, drive, folder_id: str) -> dict:
    """Doc anlegen, außer es existiert schon eins zu genau dieser Anfrage (z. B. bei Wiederholung)."""
    existing = drive.find_in_folder(folder_id, "lead_key", lead.key)
    if existing:
        return existing
    return drive.create_doc_from_html(lead.name, render_html(lead), folder_id, {"lead_key": lead.key})


def _find_existing_item(lead: Lead, monday, cat: dict, today: str) -> str | None:
    """Gleiche E-Mail am selben Tag im selben Board = Doppel (Retry oder doppelt abgeschickt)."""
    email_col = cat["columns"].get("email")
    if not lead.email or not email_col:
        return None
    for item in monday.find_items(cat["board_id"], email_col, lead.email):
        if item.get("created_at", "")[:10] >= today[:10] or _column_text(item, cat["columns"]["date"]) == today:
            return item["id"]
    return None


_COUNTRY_PREFIXES = {"352": "LU", "49": "DE", "32": "BE", "33": "FR", "31": "NL", "41": "CH", "43": "AT"}


def _phone_value(phone: str) -> dict:
    country = next((c for p, c in _COUNTRY_PREFIXES.items() if phone.startswith(p)), None)
    return {"phone": phone, "countryShortName": country} if country else {"phone": phone}


def _column_text(item: dict, column_id: str) -> str:
    return next((c.get("text") or "" for c in item.get("column_values", []) if c["id"] == column_id), "")


def _attach_doc(monday, cat: dict, item_id: str, lead: Lead, url: str) -> None:
    file_col = cat["columns"].get("file")
    if file_col:
        try:
            monday.change_column_value(
                cat["board_id"], item_id, file_col,
                {"files": [{"name": lead.name, "fileType": "GOOGLE_DRIVE", "linkToFile": url}]},
            )
            return
        except Exception as exc:  # Spalte nicht per Link befüllbar -> Link als Update, Anfrage bleibt vollständig
            log.warning("Datei-Spalte nicht befüllbar, Link als Update gepostet", flow=FLOW, item_id=item_id,
                        error=str(exc))
    monday.create_update(item_id, f'Anfrage-Dokument: <a href="{url}">{url}</a>')
