from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Sequence

from .engine import ProviderPipelineRunner
from .jobs import KCJobService
from .server import create_server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vlearn-kc-mcp")
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default="stdio",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--jobs-root",
        default=os.getenv("VLEARN_KC_MCP_JOBS_ROOT", "runs/mcp"),
    )
    parser.add_argument(
        "--owner-namespace",
        default=os.getenv("VLEARN_KC_MCP_OWNER_NAMESPACE", "local"),
    )
    parser.add_argument("--max-workers", type=int, default=2)
    parser.add_argument("--max-active-jobs", type=int, default=4)
    parser.add_argument("--max-stored-jobs", type=int, default=200)
    parser.add_argument("--max-content-units", type=int, default=5_000)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.max_workers < 1 or args.max_workers > 16:
        raise SystemExit("--max-workers must be between 1 and 16")
    if not 1 <= args.port <= 65535:
        raise SystemExit("--port must be between 1 and 65535")
    if args.transport == "streamable-http" and args.host not in {
        "127.0.0.1",
        "::1",
        "localhost",
    }:
        raise SystemExit(
            "refusing unauthenticated remote bind; use a trusted local auth proxy"
        )
    if args.max_active_jobs < 1 or args.max_active_jobs > 64:
        raise SystemExit("--max-active-jobs must be between 1 and 64")
    if args.max_stored_jobs < args.max_active_jobs or args.max_stored_jobs > 10_000:
        raise SystemExit(
            "--max-stored-jobs must be between max-active-jobs and 10000"
        )
    if args.max_content_units < 1 or args.max_content_units > 100_000:
        raise SystemExit("--max-content-units must be between 1 and 100000")
    jobs_root = Path(args.jobs_root)
    runner = ProviderPipelineRunner.from_environment()
    service = KCJobService(
        root=jobs_root,
        runner=runner,
        max_workers=args.max_workers,
        owner_namespace=args.owner_namespace,
        max_active_jobs=args.max_active_jobs,
        max_stored_jobs=args.max_stored_jobs,
        max_content_units=args.max_content_units,
    )
    server = create_server(service)
    try:
        if args.transport == "stdio":
            server.run(transport="stdio")
        else:
            server.run(
                transport="streamable-http",
                host=args.host,
                port=args.port,
            )
    finally:
        service.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
