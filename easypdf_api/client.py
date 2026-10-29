"""Minimal client for the EasyPDF public API v1 (https://www.easypdf.fr/api-docs).

Every request goes to the fixed origin https://www.easypdf.fr with the API key
in the X-API-Key header. The key is never put in an error message.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import requests

BASE_URL = "https://www.easypdf.fr/api/v1"
API_DOCS_URL = "https://www.easypdf.fr/api-docs"
PRICING_URL = "https://www.easypdf.fr/pricing"
USER_AGENT = "easypdf-dify-plugin/0.0.1"

MAX_FILE_BYTES = 50 * 1024 * 1024
CONNECT_TIMEOUT = 15
READ_TIMEOUT = 300
TRANSLATE_READ_TIMEOUT = 580

_FILENAME_RE = re.compile(r"filename\*?=(?:UTF-8'')?\"?([^\";]+)\"?", re.IGNORECASE)


class EasyPDFError(Exception):
    """An error with a message that can be shown to the Dify user as is."""

    def __init__(self, message: str, status: int | None = None, code: str | None = None):
        super().__init__(message)
        self.status = status
        self.code = code


@dataclass
class FileResult:
    content: bytes
    filename: str
    mime_type: str
    units_used: int | None
    quota_remaining: int | None
    headers: dict[str, str] = field(default_factory=dict)


def _int_header(headers: Any, name: str) -> int | None:
    value = headers.get(name)
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _filename_from(headers: Any, fallback: str) -> str:
    match = _FILENAME_RE.search(headers.get("Content-Disposition") or "")
    if not match:
        return fallback
    name = match.group(1).strip().replace("/", "_").replace("\\", "_")
    return name or fallback


def _detail(response: requests.Response) -> tuple[str | None, str | None]:
    """Return (error_code, message) from an EasyPDF error body."""
    try:
        body = response.json()
    except ValueError:
        return None, None
    detail = body.get("detail") if isinstance(body, dict) else None
    if isinstance(detail, dict):
        return detail.get("error"), detail.get("message")
    if isinstance(detail, str):
        return None, detail
    if isinstance(detail, list):
        # FastAPI request validation errors: [{"loc": [...], "msg": "..."}]
        parts = []
        for item in detail[:5]:
            if isinstance(item, dict):
                loc = ".".join(str(p) for p in item.get("loc", []) if p not in ("body", "header"))
                parts.append(f"{loc}: {item.get('msg')}" if loc else str(item.get("msg")))
        return "invalid_request", "; ".join(parts) or None
    return None, None


def error_from_response(response: requests.Response) -> EasyPDFError:
    status = response.status_code
    code, message = _detail(response)

    if status == 401:
        text = f"EasyPDF rejected the API key. Check the key in the EasyPDF plugin settings or create a new one at {API_DOCS_URL}."
    elif status == 403:
        text = message or "This EasyPDF API key cannot be used."
        text = f"{text} Create a new key at {API_DOCS_URL}."
    elif status == 402 and code == "paid_plan_required":
        text = message or f"This operation requires a paid EasyPDF plan ({PRICING_URL})."
    elif status == 402:
        text = (message or "The monthly EasyPDF quota of this API key is used up.") + f" Plans: {PRICING_URL}."
    elif status == 413:
        text = "The file is larger than the 50 MB limit of the EasyPDF API."
    elif status == 429:
        retry = response.headers.get("Retry-After")
        wait = f" Retry in {retry} seconds." if retry else " Retry in a minute."
        text = "EasyPDF rate limit reached (10 requests per minute per API key by default)." + wait
    elif status in (400, 404, 422):
        text = f"EasyPDF could not process the request: {message or f'HTTP {status}'}"
    elif status >= 500:
        text = f"EasyPDF failed to process the file (HTTP {status})."
        if message:
            text += f" {message}"
        text += " Please try again later."
    else:
        text = f"Unexpected EasyPDF response (HTTP {status})."
        if message:
            text += f" {message}"
    return EasyPDFError(text, status=status, code=code)


class EasyPDFClient:
    def __init__(self, api_key: str, session: requests.Session | None = None):
        if not api_key:
            raise EasyPDFError("The EasyPDF API key is missing. Add it in the EasyPDF plugin settings.")
        self._session = session or requests.Session()
        self._session.headers.update({"X-API-Key": api_key, "User-Agent": USER_AGENT})

    def _send(self, method: str, path: str, read_timeout: int, **kwargs: Any) -> requests.Response:
        try:
            response = self._session.request(
                method,
                f"{BASE_URL}{path}",
                timeout=(CONNECT_TIMEOUT, read_timeout),
                allow_redirects=False,
                **kwargs,
            )
        except requests.Timeout as e:
            raise EasyPDFError(f"EasyPDF did not answer within {read_timeout} seconds. Please try again.") from e
        except requests.RequestException as e:
            raise EasyPDFError("Could not reach EasyPDF (https://www.easypdf.fr). Check the network connection of your Dify instance.") from e
        if response.status_code >= 300:
            raise error_from_response(response)
        return response

    def usage(self) -> dict[str, Any]:
        response = self._send("GET", "/usage", read_timeout=30)
        try:
            return response.json()
        except ValueError as e:
            raise EasyPDFError("EasyPDF returned an unreadable usage response.") from e

    def _file_result(self, response: requests.Response, fallback_name: str) -> FileResult:
        mime_type = (response.headers.get("Content-Type") or "application/octet-stream").split(";")[0].strip()
        return FileResult(
            content=response.content,
            filename=_filename_from(response.headers, fallback_name),
            mime_type=mime_type,
            units_used=_int_header(response.headers, "X-EasyPDF-Units-Used"),
            quota_remaining=_int_header(response.headers, "X-EasyPDF-Quota-Remaining"),
            headers={k: v for k, v in response.headers.items() if k.lower().startswith("x-easypdf-")},
        )

    def process(
        self,
        path: str,
        files: list[tuple[str, tuple[str, bytes, str]]],
        data: dict[str, Any] | None = None,
        fallback_name: str = "result.pdf",
        read_timeout: int = READ_TIMEOUT,
    ) -> FileResult:
        """POST multipart/form-data to /pdf/<path> and return the produced file."""
        form = {k: str(v) for k, v in (data or {}).items() if v is not None}
        response = self._send("POST", f"/pdf/{path}", read_timeout=read_timeout, files=files, data=form)
        return self._file_result(response, fallback_name)

    def generate(self, payload: dict[str, Any]) -> FileResult:
        response = self._send("POST", "/generate/pdf", read_timeout=READ_TIMEOUT, json=payload)
        return self._file_result(response, "generated.pdf")
