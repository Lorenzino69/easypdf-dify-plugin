import json
from collections.abc import Generator
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage

import easypdf_api.tool_base as base
from easypdf_api.client import EasyPDFError

PAGE_FORMATS = ("A4", "A3", "A5", "Letter", "Legal", "Tabloid")


class GeneratePdfTool(base.EasyPDFTool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        fmt = self._choice(tool_parameters, "format", ("html", "markdown"), "html")
        content = tool_parameters.get("content")
        if not content or not str(content).strip():
            raise EasyPDFError("The 'content' parameter is required (the HTML or Markdown to render).")
        variables: Any = tool_parameters.get("variables") or {}
        if isinstance(variables, str):
            try:
                variables = json.loads(variables) if variables.strip() else {}
            except ValueError as e:
                raise EasyPDFError('The \'variables\' parameter must be a JSON object, for example {"name": "Ada"}.') from e
        if not isinstance(variables, dict):
            raise EasyPDFError('The \'variables\' parameter must be a JSON object, for example {"name": "Ada"}.')
        page_format = str(tool_parameters.get("page_format") or "A4")
        if page_format not in PAGE_FORMATS:
            raise EasyPDFError(f"The 'page_format' parameter must be one of: {', '.join(PAGE_FORMATS)}.")
        landscape = tool_parameters.get("landscape")
        if isinstance(landscape, str):
            landscape = landscape.strip().lower() in ("true", "1", "yes")
        result = self._client().generate({
            "format": fmt,
            "content": str(content),
            "variables": variables,
            "options": {"page_format": page_format, "landscape": bool(landscape)},
        })
        yield from self._emit(result)
