"""OnePage-Webhook-Payload -> einheitliche Anfrage (Lead).

Das genaue Payload-Format von OnePage ist nicht öffentlich dokumentiert.
Darum wird tolerant gelesen: entweder eine Feldliste ({label, value}) oder
ein (verschachteltes) Objekt. Kontaktfelder werden über ihre Bezeichnung
erkannt, alles Übrige wird als Frage/Antwort ins Google-Doc übernommen.
Sobald das echte Format bekannt ist (LOG_PAYLOAD=1), hier nachschärfen.
"""

import hashlib
import json
import re
from dataclasses import dataclass, field

_EMAIL = ("email", "e-mail", "e mail", "mail")
_PHONE = ("telefon", "phone", "tel", "handy", "mobil", "gsm", "téléphone")
_FIRST = ("vorname", "first name", "firstname", "first_name", "prénom", "prenom")
_LAST = ("nachname", "last name", "lastname", "last_name", "surname", "familienname", "nom de famille")
_FULL = ("name", "full name", "fullname", "full_name", "vollständiger name", "nom")
_SALUTATION = ("anrede", "salutation", "civilité")
_ROUTING = ("form", "formular", "form_name", "formname", "page", "seite", "page_url", "url", "source",
            "quelle", "funnel", "kampagne", "campaign", "title", "titel", "page_title")
_META = ("id", "uuid", "submission_id", "created_at", "updated_at", "timestamp", "date", "secret",
         "secretkey", "token", "ip", "user_agent", "useragent", "type", "event", "reason",
         "consent", "datenschutz", "privacy", "dsgvo", "gdpr", "agb")
_LIST_KEYS = ("fields", "answers", "form_data", "formdata", "values", "questions", "data")


@dataclass
class Lead:
    name: str
    email: str | None
    phone: str | None
    answers: list[tuple[str, str]] = field(default_factory=list)
    routing_text: str = ""
    key: str = ""


def _norm(label: str) -> str:
    label = re.sub(r"^\s*\d+[\.\)]?\s*", "", str(label))  # "1. Frage" -> "Frage"
    return re.sub(r"\s+", " ", label).strip().lower().rstrip(":*?").strip()


def _text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(_text(v) for v in value if _text(v))
    if isinstance(value, dict):
        for k in ("label", "value", "text", "name"):
            if k in value:
                return _text(value[k])
        return json.dumps(value, ensure_ascii=False)
    return str(value).strip()


def _field_list(obj) -> list[tuple[str, str]] | None:
    """Erkennt Listen der Form [{label|name|question, value|answer}, ...]."""
    if not isinstance(obj, list) or not obj or not all(isinstance(i, dict) for i in obj):
        return None
    out = []
    for item in obj:
        label = next((item[k] for k in ("label", "question", "title", "name", "key") if item.get(k)), None)
        if label is None:
            return None
        value = next((item[k] for k in ("value", "answer", "values", "text") if k in item), "")
        out.append((str(label), _text(value)))
    return out


def _flatten(obj, prefix="") -> list[tuple[str, str]]:
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.lower() in _LIST_KEYS and (fl := _field_list(v)) is not None:
                out.extend(fl)
            elif isinstance(v, dict):
                out.extend(_flatten(v, k))
            else:
                out.append((str(k), _text(v)))
    elif (fl := _field_list(obj)) is not None:
        out.extend(fl)
    return out


def _is(label: str, names: tuple[str, ...]) -> bool:
    n = _norm(label)
    leaf = n.rsplit(".", 1)[-1]
    return n in names or leaf in names


def payload_key(payload: dict) -> str:
    for k in ("id", "uuid", "submission_id", "lead_id"):
        if isinstance(payload.get(k), (str, int)) and str(payload[k]):
            return re.sub(r"[^A-Za-z0-9_-]", "", str(payload[k]))[:60]
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()[:24]


def parse(payload: dict) -> Lead:
    pairs = _flatten(payload)
    email = phone = first = last = full = salutation = None
    routing, answers = [], []

    for label, value in pairs:
        if not value:
            continue
        if email is None and _is(label, _EMAIL) and "@" in value:
            email = value.lower()
        elif phone is None and _is(label, _PHONE):
            phone = value
        elif first is None and _is(label, _FIRST):
            first = value
        elif last is None and _is(label, _LAST):
            last = value
        elif full is None and _is(label, _FULL):
            full = value
        elif salutation is None and _is(label, _SALUTATION):
            salutation = value
        elif _is(label, _ROUTING):
            routing.append(value)
        elif _is(label, _META):
            continue
        else:
            answers.append((re.sub(r"^\s*\d+[\.\)]?\s*", "", label).strip(), value))

    name = " ".join(p for p in (first, last) if p) or full
    if not name and last:
        name = f"{salutation} {last}" if salutation else last
    if not name:
        name = email or "Unbekannte Anfrage"

    # Für die Zuordnung zählen Formular/Seite zuerst, notfalls die Antworten selbst.
    routing_text = " | ".join(routing) or " | ".join(f"{q} {a}" for q, a in answers)
    return Lead(name=name.strip(), email=email, phone=normalize_phone(phone), answers=answers,
                routing_text=routing_text, key=payload_key(payload))


def normalize_phone(raw: str | None) -> str | None:
    """Ziffern mit Ländervorwahl ohne '+', wie bisher in monday (z. B. 352691123456)."""
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    if raw.strip().startswith("00"):
        digits = digits[2:]
    elif len(digits) in (6, 8, 9) and not raw.strip().startswith("+"):
        digits = "352" + digits  # luxemburgische Nummer ohne Vorwahl
    return digits or None


def route(lead: Lead, categories: dict) -> str | None:
    for key, cat in categories.items():
        if any(re.search(p, lead.routing_text, re.IGNORECASE) for p in cat["match"]):
            return key
    return None
