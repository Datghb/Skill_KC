from __future__ import annotations

import json
from pathlib import Path

import pytest
from mcp import Client

from test_mcp_jobs import bundle_payload, service
from vlearn_kc_mcp.server import create_server


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_mcp_server_discovers_exact_public_tools(tmp_path: Path) -> None:
    server = create_server(service(tmp_path))

    async with Client(server, raise_exceptions=True) as client:
        result = await client.list_tools()

    assert {tool.name for tool in result.tools} == {
        "validate_material_bundle",
        "start_kc_generation",
        "get_kc_job_status",
        "get_kc_draft",
        "verify_kc_run",
    }
    start = next(tool for tool in result.tools if tool.name == "start_kc_generation")
    schema_text = json.dumps(start.input_schema)
    assert "material_bundle" in schema_text
    assert "request_id" in schema_text
    assert "input_dir" not in schema_text
    assert "output_dir" not in schema_text
    assert "recorded_dir" not in schema_text
    assert '"path"' not in schema_text


@pytest.mark.anyio
async def test_mcp_tools_execute_full_offline_job_flow(tmp_path: Path) -> None:
    server = create_server(service(tmp_path))

    async with Client(server, raise_exceptions=True) as client:
        validation = await client.call_tool(
            "validate_material_bundle", {"material_bundle": bundle_payload()}
        )
        started = await client.call_tool(
            "start_kc_generation",
            {
                "material_bundle": bundle_payload(),
                "request_id": "mcp-offline-flow",
            },
        )
        job_id = started.structured_content["job_id"]
        status = await client.call_tool("get_kc_job_status", {"job_id": job_id})
        draft = await client.call_tool("get_kc_draft", {"job_id": job_id})
        verified = await client.call_tool("verify_kc_run", {"job_id": job_id})

    assert validation.structured_content["verified"] is True
    assert status.structured_content["status"] == "succeeded"
    assert draft.structured_content["status"] == "draft"
    assert verified.structured_content["verified"] is True


@pytest.mark.anyio
async def test_mcp_tool_errors_are_controlled_and_sanitized(tmp_path: Path) -> None:
    server = create_server(service(tmp_path))

    async with Client(server) as client:
        result = await client.call_tool(
            "get_kc_job_status", {"job_id": "../server-path"}
        )

    assert result.is_error is True
    message = " ".join(block.text for block in result.content if hasattr(block, "text"))
    assert "invalid job_id" in message
    assert str(tmp_path) not in message
