"""Tests mit erfundenen Daten (nie echte Kundendaten ins Repo!)."""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE.parents[2])]

import flow  # noqa: E402
import pytest  # noqa: E402
from lead import normalize_phone, parse, route  # noqa: E402

FIELD_LIST_PAYLOAD = {
    "id": "sub_123",
    "form_name": "Badezimmer Anfrage",
    "fields": [
        {"label": "Vorname", "value": "Max"},
        {"label": "Nachname", "value": "Muster"},
        {"label": "E-Mail", "value": "Max@Example.com"},
        {"label": "Telefon", "value": "691 123 456"},
        {"label": "1. Das Badezimmer wird genutzt als?", "value": "Hauptbad"},
        {"label": "Was ist Dir bei einer Zusammenarbeit wichtig?", "value": ["Beratung", "Keine Subunternehmen"]},
        {"label": "Datenschutz", "value": "akzeptiert"},
    ],
}

FLAT_PAYLOAD = {
    "page_url": "https://hausman.lu/klima",
    "contact": {"name": "Erika Beispiel", "email": "erika@example.org", "phone": "+49 151 2345678"},
    "Welche Räume sollen klimatisiert werden?": "Schlafzimmer",
}


class FakeMonday:
    def __init__(self, existing=None, file_column_fails=False):
        self.created, self.columns, self.updates = [], [], []
        self.existing = existing or []
        self.file_column_fails = file_column_fails

    def find_items(self, board_id, column_id, value):
        return self.existing

    def create_item(self, board_id, group_id, name, values):
        self.created.append((board_id, group_id, name, values))
        return "999"

    def change_column_value(self, board_id, item_id, column_id, value):
        if self.file_column_fails:
            raise RuntimeError("unsupported")
        self.columns.append((column_id, value))

    def create_update(self, item_id, body):
        self.updates.append(body)


class FakeDrive:
    def __init__(self, existing=None):
        self.created, self.existing = [], existing

    def find_in_folder(self, folder_id, key, value):
        return self.existing

    def create_doc_from_html(self, title, html, folder_id, props):
        self.created.append((title, html, folder_id, props))
        return {"id": "doc1", "webViewLink": "https://docs.google.com/document/d/doc1/edit"}


def test_parse_field_list():
    lead = parse(FIELD_LIST_PAYLOAD)
    assert lead.name == "Max Muster"
    assert lead.email == "max@example.com"
    assert lead.phone == "352691123456"
    assert lead.answers == [
        ("Das Badezimmer wird genutzt als?", "Hauptbad"),
        ("Was ist Dir bei einer Zusammenarbeit wichtig?", "Beratung, Keine Subunternehmen"),
    ]
    assert lead.key == "sub_123"


def test_parse_flat_and_route():
    lead = parse(FLAT_PAYLOAD)
    assert (lead.name, lead.email, lead.phone) == ("Erika Beispiel", "erika@example.org", "491512345678")
    assert route(lead, flow.CONFIG["categories"]) == "klima"


@pytest.mark.parametrize("raw,expected", [("00352 691 123 456", "352691123456"), ("+352691123456", "352691123456"),
                                          ("621123456", "352621123456"), (None, None)])
def test_normalize_phone(raw, expected):
    assert normalize_phone(raw) == expected


def test_handle_creates_doc_and_item():
    monday, drive = FakeMonday(), FakeDrive()
    result = flow.handle(FIELD_LIST_PAYLOAD, monday, drive, today="2026-10-19")

    assert result.status == "created" and result.category == "badezimmer"
    title, html, folder, props = drive.created[0]
    assert title == "Max Muster" and folder == flow.CONFIG["drive_folder_id"] and props == {"lead_key": "sub_123"}
    assert "Hauptbad" in html and "Datenschutz" not in html

    board, group, name, values = monday.created[0]
    assert (board, group, name) == (1476899054, "topics", "Max Muster")
    assert values == {
        "status": {"label": "Neue Anfrage eingegangen"},
        "datum": {"date": "2026-10-19"},
        "text__1": "Badezimmer",
        "e_mail__1": {"email": "max@example.com", "text": "max@example.com"},
        "telefon__1": {"phone": "352691123456", "countryShortName": "LU"},
    }
    assert monday.columns[0][0] == "datei__1"


def test_handle_skips_duplicate_and_reuses_doc():
    monday = FakeMonday(existing=[{"id": "42", "created_at": "2026-10-19T08:00:00Z", "column_values": []}])
    drive = FakeDrive(existing={"id": "doc1", "webViewLink": "https://x"})
    result = flow.handle(FIELD_LIST_PAYLOAD, monday, drive, today="2026-10-19")
    assert result.status == "duplicate" and result.item_id == "42"
    assert not monday.created and not drive.created


def test_file_column_fallback_posts_update():
    monday = FakeMonday(file_column_fails=True)
    flow.handle(FIELD_LIST_PAYLOAD, monday, FakeDrive(), today="2026-10-19")
    assert "docs.google.com" in monday.updates[0]


def test_unroutable_raises():
    with pytest.raises(flow.Unroutable):
        flow.handle({"fields": [{"label": "E-Mail", "value": "a@b.c"}, {"label": "Frage", "value": "egal"}]},
                    FakeMonday(), FakeDrive())
