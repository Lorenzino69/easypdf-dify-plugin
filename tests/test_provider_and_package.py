"""Credential validation, and consistency of the YAML declarations with the code."""

import os
import re

import pytest
import yaml
from dify_plugin import Tool, ToolProvider
from dify_plugin.core.utils.class_loader import load_single_subclass_from_source
from dify_plugin.errors.tool import ToolProviderCredentialValidationError

from conftest import BASE, FAKE_KEY, PLUGIN_DIR
from provider.easypdf import EasypdfProvider


def load_yaml(rel):
    with open(os.path.join(PLUGIN_DIR, rel), encoding="utf-8") as f:
        return yaml.safe_load(f)


# ── Credential validation ──

def test_valid_key_passes(http):
    http.get(f"{BASE}/usage", json={"month": "2026-10", "used": 0, "limit": 500, "remaining": 500, "plan": "free"})
    EasypdfProvider().validate_credentials({"api_key": FAKE_KEY})
    assert http.request_history[0].headers["X-API-Key"] == FAKE_KEY


def test_invalid_key_raises_401(http):
    http.get(f"{BASE}/usage", status_code=401,
             json={"detail": {"error": "invalid_api_key", "message": "The provided API key is invalid."}})
    with pytest.raises(ToolProviderCredentialValidationError, match="rejected the API key") as info:
        EasypdfProvider().validate_credentials({"api_key": FAKE_KEY})
    assert FAKE_KEY not in str(info.value)


def test_revoked_key_raises(http):
    http.get(f"{BASE}/usage", status_code=403,
             json={"detail": {"error": "api_key_revoked", "message": "This API key has been revoked."}})
    with pytest.raises(ToolProviderCredentialValidationError, match="revoked"):
        EasypdfProvider().validate_credentials({"api_key": FAKE_KEY})


@pytest.mark.parametrize("creds", [{}, {"api_key": ""}, {"api_key": "   "}])
def test_empty_key_raises_without_request(http, creds):
    with pytest.raises(ToolProviderCredentialValidationError, match="required"):
        EasypdfProvider().validate_credentials(creds)
    assert not http.called


# ── Declarations ──

PROVIDER = load_yaml("provider/easypdf.yaml")
TOOL_FILES = PROVIDER["tools"]


def test_manifest_points_to_existing_files():
    manifest = load_yaml("manifest.yaml")
    assert manifest["author"] == "easypdf" and manifest["name"] == "easypdf"
    assert manifest["version"] == manifest["meta"]["version"] == "0.0.1"
    assert os.path.isfile(os.path.join(PLUGIN_DIR, "_assets", manifest["icon"]))
    assert os.path.isfile(os.path.join(PLUGIN_DIR, manifest["privacy"]))
    assert manifest["plugins"]["tools"] == ["provider/easypdf.yaml"]
    assert re.fullmatch(r"https://github\.com/[\w.-]+/[\w.-]+", manifest["repo"])


def test_provider_class_loads():
    cls = load_single_subclass_from_source(
        module_name="provider.easypdf",
        script_path=os.path.join(PLUGIN_DIR, PROVIDER["extra"]["python"]["source"]),
        parent_type=ToolProvider,
    )
    assert cls is EasypdfProvider or cls.__name__ == "EasypdfProvider"


@pytest.mark.parametrize("tool_yaml", TOOL_FILES)
def test_each_tool_declaration_is_consistent(tool_yaml):
    spec = load_yaml(tool_yaml)
    name = spec["identity"]["name"]
    assert tool_yaml == f"tools/{name}.yaml"
    assert spec["identity"]["author"] == "easypdf"
    assert spec["description"]["human"]["en_US"] and spec["description"]["llm"]
    source = spec["extra"]["python"]["source"]
    assert source == f"tools/{name}.py"

    # Exactly one Tool subclass per module, as the Dify loader requires.
    load_single_subclass_from_source(
        module_name=f"tools.{name}",
        script_path=os.path.join(PLUGIN_DIR, source),
        parent_type=Tool,
    )

    for p in spec["parameters"]:
        assert p["form"] in ("llm", "form")
        assert p["label"]["en_US"] and p["human_description"]["en_US"] and p["llm_description"]
        assert p["type"] in ("string", "number", "boolean", "select", "file", "files")
        if p["type"] == "select":
            values = [o["value"] for o in p["options"]]
            assert p.get("default") is None or p["default"] in values


def test_sixteen_tools_declared():
    assert len(TOOL_FILES) == 16
    assert len(set(TOOL_FILES)) == 16
