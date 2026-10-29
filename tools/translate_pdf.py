from collections.abc import Generator
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage

import easypdf_api.tool_base as base
from easypdf_api.client import TRANSLATE_READ_TIMEOUT, EasyPDFError


class TranslatePdfTool(base.EasyPDFTool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        target = self._text(tool_parameters, "target_language", required=True) or ""
        if len(target) < 2:
            raise EasyPDFError("The 'target_language' parameter needs a language name or code, for example English or fr.")
        source = self._text(tool_parameters, "source_language", default="auto") or "auto"
        yield from self._run_simple(
            tool_parameters,
            "translate",
            {"target_language": target, "source_language": source},
            "-translated",
            read_timeout=TRANSLATE_READ_TIMEOUT,
        )
