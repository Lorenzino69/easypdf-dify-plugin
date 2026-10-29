import re
from collections.abc import Generator
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage

import easypdf_api.tool_base as base
from easypdf_api.client import EasyPDFError


class WatermarkPdfTool(base.EasyPDFTool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        text = self._text(tool_parameters, "text", required=True)
        opacity = self._number(tool_parameters, "opacity", 0.3, minimum=0, maximum=1)
        rotation = self._number(tool_parameters, "rotation", -45, minimum=-360, maximum=360)
        font_size = self._number(tool_parameters, "font_size", 60, minimum=6, maximum=300)
        color = self._text(tool_parameters, "color", default="#888888") or "#888888"
        if not color.startswith("#"):
            color = f"#{color}"
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
            raise EasyPDFError("The 'color' parameter must be a hex color like #888888.")
        yield from self._run_simple(tool_parameters, "watermark", {
            "text": text,
            "opacity": opacity,
            "rotation": rotation,
            "font_size": font_size,
            "color": color,
        }, "-watermarked")
