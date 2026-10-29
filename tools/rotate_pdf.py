from collections.abc import Generator
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage

import easypdf_api.tool_base as base


class RotatePdfTool(base.EasyPDFTool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        angle = self._choice(tool_parameters, "angle", ("90", "180", "270"), "90")
        pages = self._pages(tool_parameters, "pages", required=False)
        yield from self._run_simple(tool_parameters, "rotate", {"angle": angle, "pages": pages}, "-rotated")
