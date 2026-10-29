"""Shared helpers for the EasyPDF tools: input files, parameters, output messages."""

from __future__ import annotations

import os
import re
from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from easypdf_api.client import MAX_FILE_BYTES, EasyPDFClient, EasyPDFError, FileResult

PDF_MIME = "application/pdf"


class EasyPDFTool(Tool):
    """Base class: one subclass per EasyPDF endpoint."""

    def _client(self) -> EasyPDFClient:
        credentials = self.runtime.credentials or {}
        return EasyPDFClient(str(credentials.get("api_key") or "").strip())

    # ── Inputs ──────────────────────────────────────────────────────

    @staticmethod
    def _pdf_upload(file: Any, param: str = "file") -> tuple[str, bytes, str]:
        """Return (filename, bytes, mime) for a Dify file parameter holding a PDF."""
        if isinstance(file, list):
            file = file[0] if file else None
        if file is None:
            raise EasyPDFError(f"The '{param}' parameter needs a PDF file.")
        try:
            data = file.blob
        except Exception as e:
            raise EasyPDFError(f"Could not read the file given in '{param}': {e}") from e
        name = os.path.basename(getattr(file, "filename", None) or "document.pdf")
        if not data:
            raise EasyPDFError(f"'{name}' is empty.")
        if len(data) > MAX_FILE_BYTES:
            raise EasyPDFError(f"'{name}' is larger than the 50 MB limit of the EasyPDF API.")
        if not data[:1024].lstrip().startswith(b"%PDF"):
            raise EasyPDFError(f"'{name}' is not a PDF file.")
        if not name.lower().endswith(".pdf"):
            name = f"{name}.pdf"
        return name, data, PDF_MIME

    @staticmethod
    def _text(params: dict[str, Any], name: str, required: bool = False, default: str | None = None) -> str | None:
        value = params.get(name)
        value = default if value is None else str(value).strip()
        if required and not value:
            raise EasyPDFError(f"The '{name}' parameter is required.")
        return value or default

    @staticmethod
    def _number(
        params: dict[str, Any],
        name: str,
        default: float,
        minimum: float | None = None,
        maximum: float | None = None,
        integer: bool = False,
    ) -> float | int:
        raw = params.get(name)
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            value: float = default
        else:
            try:
                value = float(raw)
            except (TypeError, ValueError) as e:
                raise EasyPDFError(f"The '{name}' parameter must be a number.") from e
        if minimum is not None and value < minimum:
            raise EasyPDFError(f"The '{name}' parameter must be at least {minimum:g}.")
        if maximum is not None and value > maximum:
            raise EasyPDFError(f"The '{name}' parameter must be at most {maximum:g}.")
        if integer:
            if value != int(value):
                raise EasyPDFError(f"The '{name}' parameter must be a whole number.")
            return int(value)
        return value

    @staticmethod
    def _choice(params: dict[str, Any], name: str, allowed: tuple[str, ...], default: str) -> str:
        value = str(params.get(name) or default).strip().lower()
        if value not in allowed:
            raise EasyPDFError(f"The '{name}' parameter must be one of: {', '.join(allowed)}.")
        return value

    @staticmethod
    def _pages(params: dict[str, Any], name: str, required: bool) -> str | None:
        value = str(params.get(name) or "").replace(" ", "")
        if not value:
            if required:
                raise EasyPDFError(f"The '{name}' parameter is required, for example 1,3,5-7.")
            return None
        if not re.fullmatch(r"\d+(-\d+)?(,\d+(-\d+)?)*,?", value):
            raise EasyPDFError(f"The '{name}' parameter must look like 1,3,5-7 (page numbers start at 1).")
        return value.rstrip(",")

    # ── Outputs ─────────────────────────────────────────────────────

    def _emit(self, result: FileResult, extra: dict[str, Any] | None = None) -> Generator[ToolInvokeMessage, None, None]:
        yield self.create_blob_message(
            blob=result.content,
            meta={"mime_type": result.mime_type, "filename": result.filename},
        )
        summary: dict[str, Any] = {
            "filename": result.filename,
            "mime_type": result.mime_type,
            "size_bytes": len(result.content),
            "units_used": result.units_used,
            "quota_remaining": result.quota_remaining,
        }
        summary.update(extra or {})
        yield self.create_json_message(summary)

    def _run_simple(
        self,
        params: dict[str, Any],
        path: str,
        data: dict[str, Any] | None = None,
        fallback_suffix: str = "",
        fallback_ext: str = "pdf",
        read_timeout: int | None = None,
    ) -> Generator[ToolInvokeMessage, None, None]:
        """Send one PDF (parameter 'file') plus form fields and emit the result."""
        name, data_bytes, mime = self._pdf_upload(params.get("file"))
        stem = os.path.splitext(name)[0]
        kwargs: dict[str, Any] = {}
        if read_timeout:
            kwargs["read_timeout"] = read_timeout
        result = self._client().process(
            path,
            files=[("file", (name, data_bytes, mime))],
            data=data,
            fallback_name=f"{stem}{fallback_suffix}.{fallback_ext}",
            **kwargs,
        )
        yield from self._emit(result)
