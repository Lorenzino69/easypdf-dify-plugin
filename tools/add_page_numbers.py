from collections.abc import Generator
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage

import easypdf_api.tool_base as base

POSITIONS = ("bottom-center", "bottom-left", "bottom-right", "top-center", "top-left", "top-right")


class AddPageNumbersTool(base.EasyPDFTool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        position = self._choice(tool_parameters, "position", POSITIONS, "bottom-center")
        start_number = self._number(tool_parameters, "start_number", 1, minimum=0, integer=True)
        yield from self._run_simple(
            tool_parameters, "page-numbers", {"position": position, "start_number": start_number}, "-numbered"
        )
