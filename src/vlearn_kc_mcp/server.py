from __future__ import annotations

from typing import Any

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from .jobs import JobError, KCJobService


def create_server(service: KCJobService) -> MCPServer:
    server = MCPServer(
        "vlearn-kc",
        title="VLearn KC Engine",
        description="Validate course material and generate auditable draft KCs.",
        instructions=(
            "All generated KCs are drafts. Verify a run before an LMS stores it, "
            "and never treat MCP output as automatically published content."
        ),
        version="0.1.0",
    )

    def invoke(function, *args, **kwargs):
        try:
            return function(*args, **kwargs)
        except JobError as error:
            raise ToolError(str(error)) from None

    @server.tool(structured_output=True)
    def validate_material_bundle(
        material_bundle: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate inline lesson, sources, and content-unit JSON without generation."""
        return invoke(service.validate_material_bundle, material_bundle)

    @server.tool(structured_output=True)
    def start_kc_generation(
        material_bundle: dict[str, Any], request_id: str
    ) -> dict[str, Any]:
        """Queue an idempotent background job that generates draft KCs."""
        return invoke(
            service.start_kc_generation,
            material_bundle=material_bundle,
            request_id=request_id,
        )

    @server.tool(structured_output=True)
    def get_kc_job_status(job_id: str) -> dict[str, Any]:
        """Return queued, running, succeeded, or failed status for an owned job."""
        return invoke(service.get_kc_job_status, job_id)

    @server.tool(structured_output=True)
    def get_kc_draft(job_id: str) -> dict[str, Any]:
        """Return draft KC inventory, parent topics, and manifest after success."""
        return invoke(service.get_kc_draft, job_id)

    @server.tool(structured_output=True)
    def verify_kc_run(job_id: str) -> dict[str, Any]:
        """Replay and verify hashes, evidence, Ward lineage, and parent topics."""
        return invoke(service.verify_kc_run, job_id)

    return server
