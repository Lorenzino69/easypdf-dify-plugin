from collections.abc import Generator
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage

import easypdf_api.tool_base as base
from easypdf_api.client import EasyPDFError

MAX_FILES = 20


class MergePdfsTool(base.EasyPDFTool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        files = tool_parameters.get("files") or []
        if not isinstance(files, list):
            files = [files]
        if len(files) < 2:
            raise EasyPDFError("Merging needs at least two PDF files in 'files'.")
        if len(files) > MAX_FILES:
            raise EasyPDFError(f"EasyPDF merges up to {MAX_FILES} files per call; {len(files)} were given.")
        uploads = [("files", self._pdf_upload(f, "files")) for f in files]
        result = self._client().process("merge", files=uploads, fallback_name="merged.pdf")
        yield from self._emit(result, {"merged_files": len(uploads)})
