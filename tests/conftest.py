import email
import os
import sys

import pytest
import requests_mock as rm

PLUGIN_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PLUGIN_DIR not in sys.path:
    sys.path.insert(0, PLUGIN_DIR)

from dify_plugin.file.file import File, FileType  # noqa: E402

BASE = "https://www.easypdf.fr/api/v1"
FAKE_KEY = "sk_test_unit_tests_only"
PDF_BYTES = b"%PDF-1.7\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def make_file(content: bytes = PDF_BYTES, filename: str = "contract.pdf", mime: str = "application/pdf") -> File:
    f = File(
        url=f"https://dify.example/files/{filename}",
        mime_type=mime,
        filename=filename,
        extension=os.path.splitext(filename)[1],
        type=FileType.DOCUMENT,
    )
    f._blob = content
    return f


def parse_multipart(request) -> tuple[dict[str, str], list[tuple[str, str, bytes, str]]]:
    """Return (form fields, files as (field, filename, bytes, content_type))."""
    raw = b"Content-Type: " + request.headers["Content-Type"].encode() + b"\r\n\r\n" + request.body
    msg = email.message_from_bytes(raw)
    fields: dict[str, str] = {}
    files: list[tuple[str, str, bytes, str]] = []
    for part in msg.get_payload():
        name = part.get_param("name", header="content-disposition")
        filename = part.get_filename()
        payload = part.get_payload(decode=True)
        if filename is not None:
            files.append((name, filename, payload, part.get_content_type()))
        else:
            fields[name] = payload.decode()
    return fields, files


def file_response(content: bytes = PDF_BYTES, filename: str = "contract-out.pdf", mime: str = "application/pdf",
                  units: int = 1, remaining: int = 499, extra: dict | None = None) -> dict:
    headers = {
        "Content-Type": mime,
        "Content-Disposition": f'attachment; filename="{filename}"',
        "X-EasyPDF-Units-Used": str(units),
        "X-EasyPDF-Quota-Remaining": str(remaining),
    }
    headers.update(extra or {})
    return {"content": content, "headers": headers, "status_code": 200}


@pytest.fixture
def http():
    with rm.Mocker() as m:
        yield m


@pytest.fixture
def make_tool():
    def _make(cls, key: str = FAKE_KEY):
        return cls.from_credentials({"api_key": key})
    return _make
