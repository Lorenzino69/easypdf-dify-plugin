from collections.abc import Generator
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage

import easypdf_api.tool_base as base


class SplitPdfTool(base.EasyPDFTool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        pages_per_file = self._number(tool_parameters, "pages_per_file", 1, minimum=1, integer=True)
        name, data, mime = self._pdf_upload(tool_parameters.get("file"))
        result = self._client().process(
            "split",
            files=[("file", (name, data, mime))],
            data={"pages_per_file": pages_per_file},
            fallback_name=f"{name[:-4]}-split.zip",
        )
        parts = {k.lower(): v for k, v in result.headers.items()}.get("x-easypdf-parts", "")
        yield from self._emit(result, {"parts": int(parts) if parts.isdigit() else None})
