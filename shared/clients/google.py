"""Google Drive / Docs im Namen eines echten Nutzers.

Dateien werden mit einem OAuth-Refresh-Token des Drive-Besitzers angelegt
(nicht mit einem Service-Account): Service-Accounts haben keinen eigenen
Speicher und dürfen in einem privaten "Meine Ablage" keine Dateien anlegen.
Das Token erzeugt man einmalig mit scripts/google_oauth_token.py.
"""

import io

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

from shared.retry import api_retry

SCOPES = ["https://www.googleapis.com/auth/drive"]
DOC_MIME = "application/vnd.google-apps.document"


def user_credentials(oauth: dict) -> Credentials:
    """`oauth` = {"client_id", "client_secret", "refresh_token"} aus dem Secret Manager."""
    return Credentials(
        token=None,
        refresh_token=oauth["refresh_token"],
        client_id=oauth["client_id"],
        client_secret=oauth["client_secret"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
    )


class Drive:
    def __init__(self, credentials: Credentials):
        self._svc = build("drive", "v3", credentials=credentials, cache_discovery=False)

    @api_retry
    def create_doc_from_html(self, title: str, html: str, folder_id: str,
                             app_properties: dict | None = None) -> dict:
        """Legt ein Google-Doc an; Drive wandelt das HTML (inkl. Tabellen) selbst um."""
        media = MediaIoBaseUpload(io.BytesIO(html.encode("utf-8")), mimetype="text/html", resumable=False)
        body = {"name": title, "mimeType": DOC_MIME, "parents": [folder_id]}
        if app_properties:
            body["appProperties"] = app_properties
        return (
            self._svc.files()
            .create(
                body=body,
                media_body=media,
                fields="id, webViewLink",
                supportsAllDrives=True,
            )
            .execute()
        )

    @api_retry
    def find_in_folder(self, folder_id: str, app_property_key: str, app_property_value: str) -> dict | None:
        """Sucht eine Datei, die wir früher mit appProperties markiert haben (Duplikatschutz)."""
        q = (
            f"'{folder_id}' in parents and trashed = false and "
            f"appProperties has {{ key='{app_property_key}' and value='{app_property_value}' }}"
        )
        res = self._svc.files().list(q=q, fields="files(id, webViewLink)", pageSize=1,
                                     supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
        files = res.get("files", [])
        return files[0] if files else None
