from typing import Any

from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError

from easypdf_api.client import EasyPDFClient, EasyPDFError


class EasypdfProvider(ToolProvider):
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        api_key = str(credentials.get("api_key") or "").strip()
        if not api_key:
            raise ToolProviderCredentialValidationError("The EasyPDF API key is required.")
        try:
            # GET /usage costs no quota and answers 401 for an unknown key.
            EasyPDFClient(api_key).usage()
        except EasyPDFError as e:
            raise ToolProviderCredentialValidationError(str(e)) from e
