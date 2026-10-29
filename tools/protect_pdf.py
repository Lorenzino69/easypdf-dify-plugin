from collections.abc import Generator
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage

import easypdf_api.tool_base as base
from easypdf_api.client import EasyPDFError


class ProtectPdfTool(base.EasyPDFTool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        password = tool_parameters.get("password")
        if not password:
            raise EasyPDFError("The 'password' parameter is required.")
        yield from self._run_simple(tool_parameters, "protect", {"password": str(password)}, "-protected")
