import json

import pytest
import requests
from dify_plugin.entities.tool import ToolInvokeMessage

from conftest import BASE, FAKE_KEY, PDF_BYTES, file_response, make_file, parse_multipart
from easypdf_api.client import EasyPDFError
from tools.add_page_numbers import AddPageNumbersTool
from tools.compress_pdf import CompressPdfTool
from tools.edit_pdf_text import EditPdfTextTool
from tools.extract_pages import ExtractPagesTool
from tools.generate_pdf import GeneratePdfTool
from tools.get_usage import GetUsageTool
from tools.merge_pdfs import MergePdfsTool
from tools.pdf_to_excel import PdfToExcelTool
from tools.pdf_to_powerpoint import PdfToPowerpointTool
from tools.pdf_to_word import PdfToWordTool
from tools.protect_pdf import ProtectPdfTool
from tools.rotate_pdf import RotatePdfTool
from tools.split_pdf import SplitPdfTool
from tools.translate_pdf import TranslatePdfTool
from tools.unlock_pdf import UnlockPdfTool
from tools.watermark_pdf import WatermarkPdfTool

DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PPTX = "application/vnd.openxmlformats-officedocument.presentationml.presentation"


def run(tool, params):
    return list(tool.invoke(params))


def blob_and_json(messages):
    assert len(messages) == 2
    blob, summary = messages
    assert blob.type == ToolInvokeMessage.MessageType.BLOB
    assert summary.type == ToolInvokeMessage.MessageType.JSON
    return blob, summary.message.json_object


# ── One test per file tool: endpoint, form fields, file part, output ──

SIMPLE_CASES = [
    # (tool, params, endpoint, expected form fields, output filename, mime)
    (CompressPdfTool, {"quality": "low"}, "compress", {"quality": "low"}, "contract-compressed.pdf", "application/pdf"),
    (CompressPdfTool, {}, "compress", {"quality": "medium"}, "contract-compressed.pdf", "application/pdf"),
    (SplitPdfTool, {"pages_per_file": 2}, "split", {"pages_per_file": "2"}, "contract-split.zip", "application/zip"),
    (ExtractPagesTool, {"pages": "1, 3, 5-7"}, "extract-pages", {"pages": "1,3,5-7"}, "contract-pages.pdf", "application/pdf"),
    (RotatePdfTool, {"angle": "180"}, "rotate", {"angle": "180"}, "contract-rotated.pdf", "application/pdf"),
    (RotatePdfTool, {"angle": "90", "pages": "2,4-5"}, "rotate", {"angle": "90", "pages": "2,4-5"}, "contract-rotated.pdf", "application/pdf"),
    (ProtectPdfTool, {"password": "s3cret"}, "protect", {"password": "s3cret"}, "contract-protected.pdf", "application/pdf"),
    (UnlockPdfTool, {"password": "s3cret"}, "unlock", {"password": "s3cret"}, "contract-unlocked.pdf", "application/pdf"),
    (WatermarkPdfTool, {"text": "DRAFT", "opacity": 0.5, "color": "ff0000"}, "watermark",
     {"text": "DRAFT", "opacity": "0.5", "color": "#ff0000", "rotation": "-45", "font_size": "60"},
     "contract-watermarked.pdf", "application/pdf"),
    (AddPageNumbersTool, {"position": "top-right", "start_number": 3}, "page-numbers",
     {"position": "top-right", "start_number": "3"}, "contract-numbered.pdf", "application/pdf"),
    (AddPageNumbersTool, {}, "page-numbers", {"position": "bottom-center", "start_number": "1"},
     "contract-numbered.pdf", "application/pdf"),
    (PdfToWordTool, {}, "convert/word", {}, "contract.docx", DOCX),
    (PdfToExcelTool, {}, "convert/excel", {}, "contract.xlsx", XLSX),
    (PdfToPowerpointTool, {}, "convert/powerpoint", {}, "contract.pptx", PPTX),
    (TranslatePdfTool, {"target_language": "English"}, "translate",
     {"target_language": "English", "source_language": "auto"}, "contract-translated.pdf", "application/pdf"),
    (TranslatePdfTool, {"target_language": "es", "source_language": "fr"}, "translate",
     {"target_language": "es", "source_language": "fr"}, "contract-translated.pdf", "application/pdf"),
]


@pytest.mark.parametrize("cls,params,endpoint,fields,out_name,mime", SIMPLE_CASES)
def test_file_tool_calls_endpoint(http, make_tool, cls, params, endpoint, fields, out_name, mime):
    output = b"OUTPUT-BYTES"
    http.post(f"{BASE}/pdf/{endpoint}", **file_response(output, out_name, mime, units=1, remaining=41))
    messages = run(make_tool(cls), {"file": make_file(), **params})

    request = http.request_history[0]
    assert request.method == "POST"
    assert request.url == f"{BASE}/pdf/{endpoint}"
    assert request.headers["X-API-Key"] == FAKE_KEY
    sent_fields, sent_files = parse_multipart(request)
    assert sent_fields == fields
    assert sent_files == [("file", "contract.pdf", PDF_BYTES, "application/pdf")]

    blob, summary = blob_and_json(messages)
    assert blob.message.blob == output
    assert blob.meta == {"mime_type": mime, "filename": out_name}
    assert summary["filename"] == out_name
    assert summary["mime_type"] == mime
    assert summary["size_bytes"] == len(output)
    assert summary["units_used"] == 1
    assert summary["quota_remaining"] == 41


def test_compress_reports_sizes(http, make_tool):
    http.post(f"{BASE}/pdf/compress", **file_response(b"x" * 10))
    _, summary = blob_and_json(run(make_tool(CompressPdfTool), {"file": make_file(b"%PDF" + b"0" * 36)}))
    assert summary["original_size_bytes"] == 40
    assert summary["output_size_bytes"] == 10
    assert summary["reduction_percent"] == 75.0


def test_split_reports_parts(http, make_tool):
    http.post(f"{BASE}/pdf/split", **file_response(b"PK", "c-split.zip", "application/zip", extra={"X-EasyPDF-Parts": "4"}))
    _, summary = blob_and_json(run(make_tool(SplitPdfTool), {"file": make_file()}))
    assert summary["parts"] == 4


def test_translate_counts_units_per_page(http, make_tool):
    http.post(f"{BASE}/pdf/translate", **file_response(units=12, remaining=88))
    _, summary = blob_and_json(run(make_tool(TranslatePdfTool), {"file": make_file(), "target_language": "de"}))
    assert summary["units_used"] == 12
    assert summary["quota_remaining"] == 88


def test_fallback_filename_when_header_missing(http, make_tool):
    http.post(f"{BASE}/pdf/convert/word", content=b"DOCX", headers={"Content-Type": DOCX})
    blob, summary = blob_and_json(run(make_tool(PdfToWordTool), {"file": make_file(filename="report.pdf")}))
    assert blob.meta == {"mime_type": DOCX, "filename": "report.docx"}
    assert summary["units_used"] is None


def test_file_dict_from_dify_is_converted(http, make_tool, monkeypatch):
    """Dify sends file parameters as dicts; the SDK turns them into File objects."""
    from dify_plugin.file.file import File

    monkeypatch.setattr(File, "blob", property(lambda self: PDF_BYTES))
    http.post(f"{BASE}/pdf/compress", **file_response())
    dify_file = {
        "dify_model_identity": "__dify__file__",
        "url": "https://dify.example/files/abc",
        "mime_type": "application/pdf",
        "filename": "scan.pdf",
        "extension": ".pdf",
        "size": len(PDF_BYTES),
        "type": "document",
    }
    blob_and_json(run(make_tool(CompressPdfTool), {"file": dify_file}))
    _, files = parse_multipart(http.request_history[0])
    assert files[0][1] == "scan.pdf"


# ── Merge ──

def test_merge_sends_files_in_order(http, make_tool):
    http.post(f"{BASE}/pdf/merge", **file_response(filename="merged.pdf"))
    files = [make_file(PDF_BYTES + bytes([i]), f"part{i}.pdf") for i in range(3)]
    _, summary = blob_and_json(run(make_tool(MergePdfsTool), {"files": files}))
    _, sent = parse_multipart(http.request_history[0])
    assert [(f[0], f[1]) for f in sent] == [("files", "part0.pdf"), ("files", "part1.pdf"), ("files", "part2.pdf")]
    assert [f[2] for f in sent] == [PDF_BYTES + bytes([i]) for i in range(3)]
    assert summary["merged_files"] == 3


@pytest.mark.parametrize("count", [0, 1, 21])
def test_merge_rejects_bad_file_count_without_calling_api(http, make_tool, count):
    with pytest.raises(EasyPDFError):
        run(make_tool(MergePdfsTool), {"files": [make_file() for _ in range(count)]})
    assert not http.called


# ── Edit text ──

def test_edit_text_sends_json_edits_and_returns_report(http, make_tool):
    report = [{"find": "2025", "status": "replaced", "count": 2}]
    http.post(f"{BASE}/pdf/edit-text", **file_response(
        filename="contract-edited.pdf", extra={"X-EasyPDF-Edit-Report": json.dumps(report)}))
    edits = '[{"find": "2025", "replace": "2026"}, {"find": "Draft", "page": 1}]'
    _, summary = blob_and_json(run(make_tool(EditPdfTextTool), {"file": make_file(), "edits": edits}))
    fields, _ = parse_multipart(http.request_history[0])
    assert json.loads(fields["edits"]) == [
        {"find": "2025", "replace": "2026"},
        {"find": "Draft", "replace": "", "page": 1},
    ]
    assert summary["edit_report"] == report


def test_edit_text_accepts_single_object(http, make_tool):
    http.post(f"{BASE}/pdf/edit-text", **file_response())
    run(make_tool(EditPdfTextTool), {"file": make_file(), "edits": '{"find": "Old", "replace": "New"}'})
    fields, _ = parse_multipart(http.request_history[0])
    assert json.loads(fields["edits"]) == [{"find": "Old", "replace": "New"}]


@pytest.mark.parametrize("edits", ["not json", "[]", '[{"replace": "x"}]', '[{"find": "a", "page": 0}]', '"text"'])
def test_edit_text_rejects_invalid_edits(http, make_tool, edits):
    with pytest.raises(EasyPDFError):
        run(make_tool(EditPdfTextTool), {"file": make_file(), "edits": edits})
    assert not http.called


def test_edit_text_not_found_maps_422(http, make_tool):
    http.post(f"{BASE}/pdf/edit-text", status_code=422, json={
        "detail": {"error": "text_not_found", "message": "No edit matched: '2025' was not found."}})
    with pytest.raises(EasyPDFError, match="was not found"):
        run(make_tool(EditPdfTextTool), {"file": make_file(), "edits": '[{"find": "2025", "replace": "2026"}]'})


# ── Generate ──

def test_generate_posts_json(http, make_tool):
    http.post(f"{BASE}/generate/pdf", **file_response(filename="generated.pdf", remaining=10))
    params = {
        "format": "markdown",
        "content": "# Hello [[name]]",
        "variables": '{"name": "Ada"}',
        "page_format": "Letter",
        "landscape": True,
    }
    blob, summary = blob_and_json(run(make_tool(GeneratePdfTool), params))
    request = http.request_history[0]
    assert request.headers["X-API-Key"] == FAKE_KEY
    assert request.json() == {
        "format": "markdown",
        "content": "# Hello [[name]]",
        "variables": {"name": "Ada"},
        "options": {"page_format": "Letter", "landscape": True},
    }
    assert blob.meta == {"mime_type": "application/pdf", "filename": "generated.pdf"}
    assert summary["quota_remaining"] == 10


def test_generate_defaults(http, make_tool):
    http.post(f"{BASE}/generate/pdf", **file_response())
    run(make_tool(GeneratePdfTool), {"format": "html", "content": "<h1>Hi</h1>"})
    assert http.request_history[0].json()["options"] == {"page_format": "A4", "landscape": False}
    assert http.request_history[0].json()["variables"] == {}


@pytest.mark.parametrize("params", [
    {"format": "html", "content": ""},
    {"format": "html", "content": "x", "variables": "[1]"},
    {"format": "html", "content": "x", "variables": "{bad"},
    {"format": "docx", "content": "x"},
    {"format": "html", "content": "x", "page_format": "B5"},
])
def test_generate_rejects_invalid_input(http, make_tool, params):
    with pytest.raises(EasyPDFError):
        run(make_tool(GeneratePdfTool), params)
    assert not http.called


# ── Usage ──

def test_get_usage(http, make_tool):
    usage = {"month": "2026-10", "used": 12, "limit": 500, "remaining": 488, "plan": "free"}
    http.get(f"{BASE}/usage", json=usage)
    messages = run(make_tool(GetUsageTool), {})
    assert len(messages) == 1
    assert messages[0].message.json_object == usage
    assert http.request_history[0].headers["X-API-Key"] == FAKE_KEY


# ── Local input validation ──

@pytest.mark.parametrize("cls,params", [
    (CompressPdfTool, {"quality": "ultra"}),
    (SplitPdfTool, {"pages_per_file": 0}),
    (SplitPdfTool, {"pages_per_file": 1.5}),
    (ExtractPagesTool, {"pages": ""}),
    (ExtractPagesTool, {"pages": "1-a"}),
    (RotatePdfTool, {"angle": "45"}),
    (RotatePdfTool, {"angle": "90", "pages": "first"}),
    (ProtectPdfTool, {"password": ""}),
    (UnlockPdfTool, {}),
    (WatermarkPdfTool, {"text": ""}),
    (WatermarkPdfTool, {"text": "X", "opacity": 2}),
    (WatermarkPdfTool, {"text": "X", "color": "red"}),
    (AddPageNumbersTool, {"position": "middle"}),
    (TranslatePdfTool, {"target_language": ""}),
])
def test_invalid_parameters_fail_before_any_request(http, make_tool, cls, params):
    with pytest.raises(EasyPDFError):
        run(make_tool(cls), {"file": make_file(), **params})
    assert not http.called


def test_rejects_non_pdf(http, make_tool):
    with pytest.raises(EasyPDFError, match="not a PDF"):
        run(make_tool(CompressPdfTool), {"file": make_file(b"PK\x03\x04", "notes.docx")})
    assert not http.called


def test_rejects_missing_file(http, make_tool):
    with pytest.raises(EasyPDFError, match="needs a PDF"):
        run(make_tool(CompressPdfTool), {})
    assert not http.called


def test_rejects_file_over_50_mb(http, make_tool):
    big = b"%PDF-1.7\n" + b"0" * (50 * 1024 * 1024)
    with pytest.raises(EasyPDFError, match="50 MB"):
        run(make_tool(CompressPdfTool), {"file": make_file(big)})
    assert not http.called


def test_name_without_pdf_extension_gets_one(http, make_tool):
    http.post(f"{BASE}/pdf/compress", **file_response())
    run(make_tool(CompressPdfTool), {"file": make_file(filename="scan")})
    _, files = parse_multipart(http.request_history[0])
    assert files[0][1] == "scan.pdf"


# ── API error mapping ──

ERROR_CASES = [
    (401, {"detail": {"error": "invalid_api_key", "message": "The provided API key is invalid."}}, {}, "rejected the API key"),
    (403, {"detail": {"error": "api_key_revoked", "message": "This API key has been revoked."}}, {}, "revoked"),
    (402, {"detail": {"error": "quota_exceeded", "message": "This call needs 1 unit(s) and 0 remain this month."}}, {}, "0 remain this month"),
    (402, {"detail": {"error": "paid_plan_required", "message": "Translation through the API requires a paid EasyPDF plan."}}, {}, "paid EasyPDF plan"),
    (413, {"detail": {"error": "file_too_large", "message": "Files are limited to 50 MB."}}, {}, "50 MB"),
    (429, {"detail": {"error": "rate_limit_exceeded", "message": "Too many requests"}}, {"Retry-After": "42"}, "Retry in 42 seconds"),
    (400, {"detail": {"error": "wrong_password", "message": "The password is incorrect (it is case-sensitive)."}}, {}, "password is incorrect"),
    (422, {"detail": [{"loc": ["body", "quality"], "msg": "field required", "type": "missing"}]}, {}, "quality: field required"),
    (500, {"detail": {"error": "processing_failed", "message": "Compression failed: boom"}}, {}, "HTTP 500"),
    (502, None, {}, "try again later"),
]


@pytest.mark.parametrize("status,body,headers,expected", ERROR_CASES)
def test_api_errors_are_mapped(http, make_tool, status, body, headers, expected):
    kwargs = {"json": body} if body is not None else {"text": "<html>Bad gateway</html>"}
    http.post(f"{BASE}/pdf/compress", status_code=status, headers=headers, **kwargs)
    with pytest.raises(EasyPDFError) as info:
        run(make_tool(CompressPdfTool), {"file": make_file()})
    assert expected in str(info.value)
    assert info.value.status == status
    assert FAKE_KEY not in str(info.value)


def test_timeout_is_mapped(http, make_tool):
    http.post(f"{BASE}/pdf/compress", exc=requests.exceptions.ReadTimeout)
    with pytest.raises(EasyPDFError, match="did not answer"):
        run(make_tool(CompressPdfTool), {"file": make_file()})


def test_connection_error_is_mapped(http, make_tool):
    http.post(f"{BASE}/pdf/compress", exc=requests.exceptions.ConnectionError)
    with pytest.raises(EasyPDFError, match="Could not reach EasyPDF"):
        run(make_tool(CompressPdfTool), {"file": make_file()})


def test_redirects_are_not_followed(http, make_tool):
    http.post(f"{BASE}/pdf/compress", status_code=302, headers={"Location": "https://elsewhere.example/"})
    with pytest.raises(EasyPDFError, match="HTTP 302"):
        run(make_tool(CompressPdfTool), {"file": make_file()})
    assert http.call_count == 1


def test_missing_api_key(http, make_tool):
    with pytest.raises(EasyPDFError, match="API key is missing"):
        run(make_tool(CompressPdfTool, key=""), {"file": make_file()})
    assert not http.called
