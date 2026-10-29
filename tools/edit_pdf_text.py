import json
from collections.abc import Generator
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage

import easypdf_api.tool_base as base
from easypdf_api.client import EasyPDFError

MAX_EDITS = 50


def parse_edits(raw: Any) -> list[dict[str, Any]]:
    """Accept a JSON list of {find, replace, page?} objects, or one such object."""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError as e:
            raise EasyPDFError(
                'The \'edits\' parameter must be JSON, for example [{"find": "2025", "replace": "2026"}].'
            ) from e
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list) or not raw:
        raise EasyPDFError('The \'edits\' parameter must be a non-empty JSON list of {"find": ..., "replace": ...} objects.')
    if len(raw) > MAX_EDITS:
        raise EasyPDFError(f"Up to {MAX_EDITS} edits are accepted per call.")
    edits = []
    for i, item in enumerate(raw, start=1):
        if not isinstance(item, dict) or not str(item.get("find") or "").strip():
            raise EasyPDFError(f"Edit {i} needs a non-empty \"find\" text.")
        edit: dict[str, Any] = {"find": str(item["find"]), "replace": str(item.get("replace") or "")}
        if item.get("page") not in (None, ""):
            try:
                page = int(item["page"])
            except (TypeError, ValueError) as e:
                raise EasyPDFError(f"Edit {i}: \"page\" must be a page number (1 for the first page).") from e
            if page < 1:
                raise EasyPDFError(f"Edit {i}: \"page\" must be 1 or more.")
            edit["page"] = page
        edits.append(edit)
    return edits


class EditPdfTextTool(base.EasyPDFTool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        edits = parse_edits(tool_parameters.get("edits"))
        name, data, mime = self._pdf_upload(tool_parameters.get("file"))
        result = self._client().process(
            "edit-text",
            files=[("file", (name, data, mime))],
            data={"edits": json.dumps(edits, ensure_ascii=False)},
            fallback_name=f"{name[:-4]}-edited.pdf",
        )
        raw_report = {k.lower(): v for k, v in result.headers.items()}.get("x-easypdf-edit-report")
        try:
            report = json.loads(raw_report) if raw_report else None
        except ValueError:
            report = None
        yield from self._emit(result, {"edit_report": report})
