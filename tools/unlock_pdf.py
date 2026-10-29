from collections.abc import Generator
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage

import easypdf_api.tool_base as base
from easypdf_api.client import EasyPDFError


class UnlockPdfTool(base.EasyPDFTool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        password = tool_parameters.get("password")
        if not password:
            raise EasyPDFError("The 'password' parameter is required (the current password of the PDF).")
        yield from self._run_simple(tool_parameters, "unlock", {"password": str(password)}, "-unlocked")
