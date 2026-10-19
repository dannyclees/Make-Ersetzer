"""Schlanker Client für die monday.com GraphQL-API."""

import json

import requests

from shared.retry import TransientError, api_retry

API_URL = "https://api.monday.com/v2"
API_VERSION = "2025-04"

_TRANSIENT_CODES = {"ComplexityException", "RATE_LIMIT_EXCEEDED", "maxConcurrencyExceeded", "INTERNAL_SERVER_ERROR"}


class MondayError(RuntimeError):
    pass


class MondayClient:
    def __init__(self, token: str, session: requests.Session | None = None):
        self._session = session or requests.Session()
        self._session.headers.update(
            {"Authorization": token, "API-Version": API_VERSION, "Content-Type": "application/json"}
        )

    @api_retry
    def query(self, query: str, variables: dict | None = None) -> dict:
        resp = self._session.post(API_URL, json={"query": query, "variables": variables or {}}, timeout=30)
        resp.raise_for_status()
        body = resp.json()
        errors = body.get("errors") or ([body] if body.get("error_code") else [])
        if errors:
            codes = {(e.get("extensions") or {}).get("code") or e.get("error_code") for e in errors}
            if codes & _TRANSIENT_CODES:
                raise TransientError(f"monday vorübergehend nicht verfügbar: {errors}")
            raise MondayError(f"monday API-Fehler: {errors}")
        return body["data"]

    def create_item(self, board_id: int, group_id: str, name: str, column_values: dict) -> str:
        data = self.query(
            """
            mutation ($board: ID!, $group: String!, $name: String!, $values: JSON!) {
              create_item(board_id: $board, group_id: $group, item_name: $name,
                          column_values: $values, create_labels_if_missing: false) { id }
            }
            """,
            {"board": board_id, "group": group_id, "name": name, "values": json.dumps(column_values)},
        )
        return data["create_item"]["id"]

    def change_column_value(self, board_id: int, item_id: str, column_id: str, value: dict) -> None:
        self.query(
            """
            mutation ($board: ID!, $item: ID!, $column: String!, $value: JSON!) {
              change_column_value(board_id: $board, item_id: $item, column_id: $column, value: $value) { id }
            }
            """,
            {"board": board_id, "item": item_id, "column": column_id, "value": json.dumps(value)},
        )

    def create_update(self, item_id: str, body: str) -> None:
        self.query(
            "mutation ($item: ID!, $body: String!) { create_update(item_id: $item, body: $body) { id } }",
            {"item": item_id, "body": body},
        )

    def find_items(self, board_id: int, column_id: str, value: str) -> list[dict]:
        """Items eines Boards, deren Spalte `column_id` genau `value` enthält."""
        data = self.query(
            """
            query ($board: ID!, $column: String!, $value: CompareValue!) {
              items_page_by_column_values(limit: 50, board_id: $board,
                columns: [{column_id: $column, column_values: [$value]}]) {
                items { id name created_at column_values { id text } }
              }
            }
            """,
            {"board": board_id, "column": column_id, "value": value},
        )
        return data["items_page_by_column_values"]["items"]
