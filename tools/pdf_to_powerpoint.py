from collections.abc import Generator
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage

import easypdf_api.tool_base as base


class PdfToPowerpointTool(base.EasyPDFTool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        yield from self._run_simple(tool_parameters, "convert/powerpoint", fallback_ext="pptx")
