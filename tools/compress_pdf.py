from collections.abc import Generator
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage

import easypdf_api.tool_base as base


class CompressPdfTool(base.EasyPDFTool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        quality = self._choice(tool_parameters, "quality", ("low", "medium", "high"), "medium")
        name, data, mime = self._pdf_upload(tool_parameters.get("file"))
        result = self._client().process(
            "compress",
            files=[("file", (name, data, mime))],
            data={"quality": quality},
            fallback_name=f"{name[:-4]}-compressed.pdf",
        )
        original = len(data)
        output = len(result.content)
        yield from self._emit(result, {
            "original_size_bytes": original,
            "output_size_bytes": output,
            "reduction_percent": round((1 - output / original) * 100, 1),
        })
