# EasyPDF

- **Author:** easypdf
- **Version:** 0.0.1
- **Type:** tool
- **Source repository:** https://github.com/Lorenzino69/easypdf-dify-plugin

## Overview

This plugin connects Dify to the [EasyPDF](https://www.easypdf.fr) API. It gives your workflows, chatflows and agents 16 tools: compress, merge, split, extract pages, rotate, protect with a password, unlock, add a watermark, add page numbers, replace text inside a PDF, convert to Word, Excel or PowerPoint, translate, generate a PDF from HTML or Markdown, and check your API usage.

Each tool takes a PDF from Dify (a file uploaded by the user or produced by an earlier node), sends it to the EasyPDF API, and returns the resulting file to Dify together with a small JSON summary (file name, size, units used, units remaining this month).

## Setup

### 1. Get an EasyPDF API key

1. Open the [EasyPDF API page](https://www.easypdf.fr/api-docs) and sign in (a free account works).
2. In the API key console on that page, click **Create API Key**.
3. Copy the key. It is shown only once.

Plans and monthly quotas are listed on the [API page](https://www.easypdf.fr/api-docs) and on the [pricing page](https://www.easypdf.fr/pricing).

### 2. Install and configure the plugin in Dify

1. In Dify, open **Plugins**, search the Marketplace for **EasyPDF** and install it.
2. Open the plugin's authorization settings (Dify also asks for them the first time an EasyPDF tool is used) and paste your EasyPDF API key.
3. Dify checks the key by calling `GET /api/v1/usage`. An invalid or revoked key is rejected with a message.

The key is stored by Dify as a secret credential and is sent only to EasyPDF, in the `X-API-Key` header.

## Usage

- **Workflow or chatflow:** add an EasyPDF tool node, set its file input to a file variable (for example the user's upload from the Start node) and fill in the other parameters. The produced file is available in the node's `files` output, and the summary in its `json` output.
- **Agent:** enable the EasyPDF tools you need in the agent's tool list. The agent can call them with the files attached to the conversation.

Example: a chatflow where the user uploads a contract, an **Edit PDF Text** node replaces `2025` with `2026`, then a **Protect PDF** node adds a password before the file is returned to the user.

### Output

Every file tool returns:

- the resulting file (PDF, ZIP, DOCX, XLSX or PPTX) with the right MIME type and file name;
- a JSON message such as:

```json
{
  "filename": "contract-compressed.pdf",
  "mime_type": "application/pdf",
  "size_bytes": 182344,
  "units_used": 1,
  "quota_remaining": 412
}
```

Some tools add fields: `original_size_bytes`, `output_size_bytes` and `reduction_percent` for Compress PDF, `parts` for Split PDF, `merged_files` for Merge PDFs, and `edit_report` (replacements made per edit) for Edit PDF Text.

## Tools

All PDF inputs accept one file of up to 50 MB.

### Compress PDF

Reduces the size of a PDF. Same engine as [Compress PDF on EasyPDF](https://www.easypdf.fr/tools/compress).

| Parameter | Required | Description |
| --- | --- | --- |
| `file` | yes | The PDF to compress. |
| `quality` | no | `low` (smallest file), `medium` (default) or `high` (best image quality). |

### Merge PDFs

Combines 2 to 20 PDFs into one, in the order given. Web version: [Merge PDF](https://www.easypdf.fr/tools/merge).

| Parameter | Required | Description |
| --- | --- | --- |
| `files` | yes | 2 to 20 PDF files, in order. |

### Split PDF

Splits a PDF into parts of N pages and returns a ZIP archive of PDFs. Web version: [Split PDF](https://www.easypdf.fr/tools/split).

| Parameter | Required | Description |
| --- | --- | --- |
| `file` | yes | The PDF to split. |
| `pages_per_file` | no | Pages per part, default 1 (one PDF per page). At most 100 parts. |

### Extract Pages

Keeps only the listed pages, in the order listed.

| Parameter | Required | Description |
| --- | --- | --- |
| `file` | yes | The source PDF. |
| `pages` | yes | Pages and ranges, 1-based, for example `1,3,5-7`. |

### Rotate PDF

Rotates every page, or only some pages, clockwise. Web version: [Rotate PDF](https://www.easypdf.fr/tools/rotate).

| Parameter | Required | Description |
| --- | --- | --- |
| `file` | yes | The PDF to rotate. |
| `angle` | yes | `90`, `180` or `270`. |
| `pages` | no | Pages to rotate, for example `2,4-5`. Empty means all pages. |

### Protect PDF

Encrypts a PDF with a password (AES-256). Web version: [Protect PDF](https://www.easypdf.fr/tools/protect).

| Parameter | Required | Description |
| --- | --- | --- |
| `file` | yes | The PDF to protect. |
| `password` | yes | The password needed to open the PDF. |

### Unlock PDF

Removes the password of a PDF you own. Web version: [Unlock PDF](https://www.easypdf.fr/tools/unlock).

| Parameter | Required | Description |
| --- | --- | --- |
| `file` | yes | The protected PDF. |
| `password` | yes | Its current password (case-sensitive). |

### Add Watermark

Stamps a text watermark on every page. Web version: [Add a watermark to a PDF](https://www.easypdf.fr/tools/watermark).

| Parameter | Required | Description |
| --- | --- | --- |
| `file` | yes | The PDF to watermark. |
| `text` | yes | Watermark text, for example `CONFIDENTIAL`. |
| `opacity` | no | 0 to 1, default 0.3. |
| `color` | no | Hex color, default `#888888`. |
| `rotation` | no | Text angle in degrees, default -45. |
| `font_size` | no | Font size in points, default 60. |

### Add Page Numbers

Numbers the pages. Web version: [Add page numbers to a PDF](https://www.easypdf.fr/tools/page-numbers).

| Parameter | Required | Description |
| --- | --- | --- |
| `file` | yes | The PDF to number. |
| `position` | no | `bottom-center` (default), `bottom-left`, `bottom-right`, `top-center`, `top-left` or `top-right`. |
| `start_number` | no | Number printed on the first page, default 1. |

### Edit PDF Text

Replaces or deletes text inside an existing PDF. The original fonts, sizes, colors and layout are kept, so the result is the same document with the text changed, not a new document. Web version: [Edit PDF](https://www.easypdf.fr/tools/edit).

| Parameter | Required | Description |
| --- | --- | --- |
| `file` | yes | The PDF to edit. |
| `edits` | yes | JSON list of changes (up to 50), see below. |

```json
[
  {"find": "2025", "replace": "2026"},
  {"find": "Draft", "replace": "", "page": 1}
]
```

`find` is the text exactly as printed in the PDF; keep it short (one line or a few words). An empty or missing `replace` deletes the text. `page` (1-based) limits a change to one page. If none of the `find` texts is found, the tool fails with a message and no unit is used.

### PDF to Word, PDF to Excel, PDF to PowerPoint

Convert a PDF into an editable `.docx`, an `.xlsx` with tables extracted into cells, or a `.pptx` with one slide per page. Web versions: [PDF to Word](https://www.easypdf.fr/tools/convert/pdf-to-word), [PDF to Excel](https://www.easypdf.fr/tools/convert/pdf-to-excel), [PDF to PowerPoint](https://www.easypdf.fr/tools/convert/pdf-to-ppt).

| Parameter | Required | Description |
| --- | --- | --- |
| `file` | yes | The PDF to convert. |

### Translate PDF

Translates a PDF and returns a PDF with the layout kept. Web version: [Translate PDF](https://www.easypdf.fr/tools/translate).

| Parameter | Required | Description |
| --- | --- | --- |
| `file` | yes | The PDF to translate (50 pages max per call). |
| `target_language` | yes | Language name or code, for example `English`, `fr` or `es`. |
| `source_language` | no | Language of the PDF, default `auto` (detected). |

Translation through the API requires a paid EasyPDF plan and costs 1 unit per page. Long documents can take several minutes.

### Generate PDF

Creates a PDF from HTML or Markdown. Placeholders written `{{name}}` or `[[name]]` are replaced with the values in `variables`. If a Dify field treats `{{...}}` as a template, use the `[[name]]` form instead. Web versions: [HTML to PDF](https://www.easypdf.fr/tools/convert/html-to-pdf), [Markdown to PDF](https://www.easypdf.fr/tools/convert/markdown-to-pdf).

| Parameter | Required | Description |
| --- | --- | --- |
| `format` | yes | `html` (default) or `markdown`. |
| `content` | yes | The HTML or Markdown source. |
| `variables` | no | JSON object, for example `{"name": "Ada", "total": "120 EUR"}`. |
| `page_format` | no | `A4` (default), `A3`, `A5`, `Letter`, `Legal` or `Tabloid`. |
| `landscape` | no | `true` for landscape, default `false`. |

### Get API Usage

Returns the usage of the current month for your key: `month`, `used`, `limit`, `remaining` and `plan`. It does not consume any unit.

## Limits

- **File size:** 50 MB per file.
- **Rate limit:** 10 requests per minute per API key by default. Above it, the tool fails with a message telling you when to retry.
- **Quota:** each call costs 1 unit, except Translate PDF (1 unit per page). Failed calls use no units. When the monthly quota is used up, tools fail with a "quota" message until the next month or a plan change.
- **Merge:** 2 to 20 files per call. **Split:** at most 100 parts. **Edit PDF Text:** up to 50 edits per call. **Translate PDF:** 50 pages per call, paid plan only.
- **Password-protected PDFs** must be unlocked with Unlock PDF before other tools can read them.

## Connection requirements

The plugin makes HTTPS requests to one host only: `https://www.easypdf.fr/api/v1` (endpoints `/pdf/*`, `/generate/pdf` and `/usage`). A self-hosted Dify instance needs outbound HTTPS access to `www.easypdf.fr` on port 443. No proxy, callback URL or inbound connection is needed.

## Errors

Errors from the API are turned into readable messages, for example:

- invalid or revoked API key: check the key in the plugin settings or create a new one;
- quota used up or paid plan required: the message links to the plans;
- file over 50 MB, not a PDF, wrong password, page range outside the document;
- rate limit reached: retry after the number of seconds given.

## Privacy

Files are sent to EasyPDF only to be processed and are returned in the same call. See [PRIVACY.md](PRIVACY.md) and the [EasyPDF privacy policy](https://www.easypdf.fr/confidentialite).

## Support

- API documentation: [www.easypdf.fr/api-docs](https://www.easypdf.fr/api-docs)
- Issues with this plugin: [GitHub issues](https://github.com/Lorenzino69/easypdf-dify-plugin/issues)
- Contact: hello@easypdf.fr
