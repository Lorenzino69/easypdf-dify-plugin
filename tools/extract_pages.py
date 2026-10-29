from collections.abc import Generator
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage

import easypdf_api.tool_base as base


class ExtractPagesTool(base.EasyPDFTool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        pages = self._pages(tool_parameters, "pages", required=True)
        yield from self._run_simple(tool_parameters, "extract-pages", {"pages": pages}, "-pages")
