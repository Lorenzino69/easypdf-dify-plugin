# Privacy Policy

This policy covers the EasyPDF plugin for Dify. The plugin is a thin client for the EasyPDF API operated by [EasyPDF](https://www.easypdf.fr). The full EasyPDF privacy policy is at [www.easypdf.fr/confidentialite](https://www.easypdf.fr/confidentialite).

## Data the plugin sends

The plugin itself does not collect, store or log any user data. When a tool runs, it sends the following to the EasyPDF API at `https://www.easypdf.fr/api/v1` over HTTPS, and to no other destination:

- your EasyPDF API key, in the `X-API-Key` header, to authenticate the call;
- the file or files given to the tool (for example the PDF to compress, merge or translate);
- the tool parameters (for example the watermark text, the page range, the passwords given to Protect PDF or Unlock PDF, the text edits, the target language, or the HTML or Markdown content and variables of Generate PDF).

The API key is stored by Dify as a secret credential. The plugin never writes it to logs and never includes it in error messages.

## How EasyPDF processes the data

- Files are processed only to perform the requested operation, and the result is returned in the same API call. Files sent through the API are not saved in your EasyPDF account documents, and files processed by the tools are deleted right after processing.
- EasyPDF stores, per API key, the number of units used each month to apply quotas and rate limits.
- Some operations use subprocessors listed in the EasyPDF privacy policy: PDF to Word, Excel and PowerPoint conversions can be performed by Adobe PDF Services, and Translate PDF sends the text of the document to an AI model provider. Translated text segments may be cached for up to 48 hours to avoid translating the same text twice.
- Requests pass through Cloudflare (network proxy) and are processed on servers hosted by Railway in the European Union (Netherlands).

## Data shared with third parties

Apart from EasyPDF and the subprocessors named in the EasyPDF privacy policy, no data is shared with any third party by this plugin.

## Retention and deletion

The plugin keeps nothing. Retention on the EasyPDF side is described in section 6 of the [EasyPDF privacy policy](https://www.easypdf.fr/confidentialite). You can revoke an API key at any time from the [EasyPDF API page](https://www.easypdf.fr/api-docs), and delete your EasyPDF account from your account settings.

## Contact

For privacy questions or a data processing agreement (DPA), write to hello@easypdf.fr.
