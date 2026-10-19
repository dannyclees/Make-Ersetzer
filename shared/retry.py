"""Einheitliche Wiederholversuche für API-Aufrufe.

Wiederholt wird nur bei vorübergehenden Fehlern (Netzwerk, 429, 5xx).
Fachliche Fehler (400, 401, 403, 404) schlagen sofort fehl, damit sie
nicht still verschluckt werden.
"""

import requests
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential


class TransientError(Exception):
    """Fehler, bei dem sich ein erneuter Versuch lohnt."""


def _is_transient(exc: BaseException) -> bool:
    if isinstance(exc, (TransientError, requests.ConnectionError, requests.Timeout)):
        return True
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        return exc.response.status_code == 429 or exc.response.status_code >= 500
    status = getattr(getattr(exc, "resp", None), "status", None)  # googleapiclient.HttpError
    if status is not None:
        return int(status) == 429 or int(status) >= 500
    return False


api_retry = retry(
    retry=retry_if_exception(_is_transient),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=1, max=20),
    reraise=True,
)
