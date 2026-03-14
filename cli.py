#!/usr/bin/env python3
"""CLI for project-reporter.

Usage:
    python cli.py extract <project>     # Run extractors only, print metadata
    python cli.py ingest <project>      # Full pipeline: extract → generate → write
    python cli.py build                 # Build all MkDocs sites
    python cli.py serve [project]       # Serve a project site (or hub)
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def cmd_extract(project_name: str) -> None:
    from ingestion.pipeline import IngestionPipeline

    pipeline = IngestionPipeline()
    metadata = pipeline.extract(project_name)
    print(metadata.to_context_string())
    print(f"\n--- Summary ---")
    print(f"Repos: {len(metadata.repos)}")
    print(f"Routes: {len(metadata.all_routes)}")
    print(f"MCP tools: {len(metadata.all_mcp_tools)}")
    print(f"DB tables: {len(metadata.all_tables)}")
    print(f"Frameworks: {', '.join(metadata.all_frameworks)}")


def cmd_ingest(project_name: str, sections: list[str] | None = None) -> None:
    from ingestion.pipeline import IngestionPipeline

    pipeline = IngestionPipeline()
    pipeline.ingest_project(project_name, sections=sections)


def cmd_build() -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_all.py")],
        check=True,
    )


def cmd_serve(project: str | None = None) -> None:
    if project:
        site_dir = ROOT / "projects" / project
    else:
        site_dir = ROOT / "hub"

    if not (site_dir / "mkdocs.yml").exists():
        print(f"No mkdocs.yml found in {site_dir}")
        sys.exit(1)

    subprocess.run(["mkdocs", "serve"], cwd=str(site_dir), check=True)


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    if command == "extract":
        if len(sys.argv) < 3:
            print("Usage: python cli.py extract <project>")
            sys.exit(1)
        cmd_extract(sys.argv[2])

    elif command == "ingest":
        if len(sys.argv) < 3:
            print("Usage: python cli.py ingest <project>")
            sys.exit(1)
        sections = sys.argv[3:] if len(sys.argv) > 3 else None
        cmd_ingest(sys.argv[2], sections)

    elif command == "build":
        cmd_build()

    elif command == "serve":
        project = sys.argv[2] if len(sys.argv) > 2 else None
        cmd_serve(project)

    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
